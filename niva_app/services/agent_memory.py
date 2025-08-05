import os
import uuid
import logging
import requests
import threading

import rest_framework.exceptions
from google.cloud import storage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import CSVLoader, PyPDFLoader, WebBaseLoader
from langchain_community.vectorstores.chroma import Chroma
from google import genai
from unstructured_client.models import operations, shared
import urllib.parse

from niva_app.management.commands.query_agent_memory import gemini_client
from niva_app.models import Agent, Memory, Company, WebsiteSource, MemoryType
from app.config import FRONTEND_URL, GCS_BASE_URL
from niva_app.lib.utils import FileType, FileTypeInfo
from app.config import GCS_BUCKET_NAME
from niva_app.models import WebsiteEmbeddings
from niva_app.models.rag import Document
from niva_app.services.rag import process_website, process_pdf
from niva_app.services.storage import StorageService

PERSIST_DIRECTORY = "./chroma_db"

logger = logging.getLogger("root")

class MemoryService:
    def __init__(self, company: Company):
        self.company = company
        print(self.company)
        self.collection_name = f"company-{self.company.pk}"

    def delete_memory(self, id: str):
        try:
            # Get single memory directly instead of filtering
            memory = Memory.objects.get(company=self.company, id=id)

            # Delete related objects based on memory type
            if memory.type == "website":
                WebsiteEmbeddings.objects.filter(company=self.company).delete()
                WebsiteSource.objects.filter(company=self.company).delete()
            else:
                Document.objects.filter(memory=memory).delete()

            # Delete associated storage file if exists
            if memory.url and GCS_BASE_URL in memory.url:
                try:
                    StorageService.delete_blob(GCS_BUCKET_NAME, memory.url)
                except Exception as e:
                    logger.error(f"Failed to delete storage file: {e}")

            # Delete the memory itself
            memory.delete()

        except Memory.DoesNotExist:
            raise rest_framework.exceptions.NotFound(f"Memory with id {id} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to delete memory: {e}")

    def add_memory(self, memory_type: str, url: str, name: str):
        try: 
            if memory_type == MemoryType.DOCUMENT:
                file_type = FileTypeInfo.get_file_type(url)
                if file_type == FileType.PDF:
                    self.add_pdf_memory(url, name)  
                else:
                    Memory.objects.create(
                        company=self.company,
                        url=url,
                        type=MemoryType.DOCUMENT,
                        name=name
                    )
            elif memory_type == MemoryType.WEBSITE:
                self.add_website_memory(url, name)
        
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise  # Re-raise the exception so the API returns proper error

    def _create_pgvector_website_memory(self, url):
        thread_id = threading.get_ident()
        logger.info(f"Running crawling and embedding on separate thread for {url}, thread id = {thread_id}")
        process_website(url=url, company_id=self.company.id)

    def add_website_memory(self, url: str, name: str):
        logger.info(f"Creating embeddings for website {url}, company_id: {self.company.id}")
        thread = threading.Thread(target=self._create_pgvector_website_memory, args=(url,))       
        thread.start()
        memory = Memory(
            company=self.company, 
            url=url, 
            type=MemoryType.WEBSITE,
            name=name
        )
        memory.save()

    def add_pdf_memory(self, url: str, name: str) -> Memory: 
        """
        Process a PDF and store its contents with vector embeddings
        """
        source_url = f"{GCS_BASE_URL.rstrip('/')}/{GCS_BUCKET_NAME.rstrip('/')}/{url.lstrip('/')}"
        logger.info(f"Attempting to download PDF from: {source_url}")

        # Create memory instance
        memory = Memory.objects.create(
            url=url,
            type=MemoryType.DOCUMENT,
            company=self.company,
            name=name  
        )

        try:
            storage_client = StorageService.get_client()
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(url)
            
            # Check if blob exists
            if not blob.exists():
                raise ValueError(f"File not found in storage: {url}")
            
            # Download the file content
            pdf_content = blob.download_as_bytes()
            logger.info(f"Successfully downloaded PDF from GCS: {url}")
            
            # Decode URL-encoded filename for local storage
            decoded_filename = urllib.parse.unquote(os.path.basename(url))
            
            # Create a safe local path
            safe_filename = "".join(c for c in decoded_filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            local_path = f"./pdf-data/{memory.id}_{safe_filename}"
            
            # Ensure directory exists
            local_directory = os.path.dirname(local_path)
            os.makedirs(local_directory, exist_ok=True)
            
            # Save PDF locally
            with open(local_path, "wb") as f:
                f.write(pdf_content)
            
            logger.info(f"PDF saved locally: {local_path}")

            # Process PDF with PyMuPDF
            documents = process_pdf(local_path)

            if not documents:
                logger.warning(f"No text content extracted from PDF: {local_path}")
                raise ValueError(f"No text content extracted from PDF: {safe_filename}")

            logger.info(f"Extracted {len(documents)} chunks from PDF")

            # Create embeddings for all documents at once
            embeddings_response = gemini_client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=documents
            )

            embeddings_list = [embedding.values for embedding in embeddings_response.embeddings]

            logger.info(f"Generated {len(embeddings_list)} embeddings")
            
            document_instances = [
                Document(
                    id=uuid.uuid4(),
                    content=doc_content,
                    embedding=embedding,
                    memory=memory
                )
                for doc_content, embedding in zip(documents, embeddings_list)
            ]

            # Bulk create documents
            Document.objects.bulk_create(
                document_instances,
                batch_size=1000 
            )
            
            logger.info(f"Successfully processed PDF: {safe_filename} with {len(document_instances)} chunks")
            memory.save()
            return memory

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            memory.delete()
            raise e
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            memory.delete()
            raise ValueError(f"Failed to process PDF: {str(e)}")
        finally:
            # Clean up local file
            if 'local_path' in locals() and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    logger.info(f"Cleaned up local file: {local_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up local file {local_path}: {e}")
    
    def categorize_uploaded_document(self, memory: Memory):
        """Categorize uploaded document to improve context extraction."""
        try:
            documents = Document.objects.filter(memory=memory)
            if not documents.exists():
                return
            
            sample_content = documents.first().content[:2000]
            
            categorization_prompt = f"""
            Analyze this document content and categorize it. What type of company information does this contain?
            
            Content: {sample_content}
            
            Categories:
            - COMPANY_PROFILE: About company, mission, values
            - PRODUCT_CATALOG: Products/services information  
            - SALES_MATERIAL: Sales scripts, talking points
            - POLICIES: Company policies, procedures
            - FAQ: Frequently asked questions
            - TRAINING: Training materials, guidelines
            - OTHER: Other type of content
            
            Respond with just the category name.
            """
            
            response = gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[categorization_prompt]
            )
            
            category = response.text.strip()
            
            # You could store this category in a new field or as metadata
            # For now, we'll just log it
            logger.info(f"Document categorized as: {category}")
            
        except Exception as e:
            logger.error(f"Error categorizing document: {e}")