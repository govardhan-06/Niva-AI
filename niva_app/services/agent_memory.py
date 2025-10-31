import os
import uuid
import logging
import requests
import threading
import shutil
from pathlib import Path
import tempfile

import rest_framework.exceptions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import CSVLoader, PyPDFLoader, WebBaseLoader
from langchain_community.vectorstores.chroma import Chroma
from google import genai
from unstructured_client.models import operations, shared
import urllib.parse

from niva_app.management.commands.query_agent_memory import gemini_client 
from niva_app.lib.llm import groq_client 
from niva_app.models import Agent, Memory, Course, MemoryType
from niva_app.lib.utils import FileType, FileTypeInfo
from niva_app.models.rag import Document
from niva_app.services.rag import process_pdf
from niva_app.services.s3_storage import S3StorageService

PERSIST_DIRECTORY = "./chroma_db"

logger = logging.getLogger("root")

class MemoryService:
    def __init__(self, course: Course):
        self.course = course
        self.collection_name = f"course-{self.course.pk}"
        self.storage_service = S3StorageService()

    def delete_memory(self, id: str):
        try:
            memory = Memory.objects.get(course=self.course, id=id)

            Document.objects.filter(memory=memory).delete()

            # Delete associated S3 file if exists
            if memory.url and not memory.url.startswith('http'):
                try:
                    self.storage_service.delete_file(memory.url)
                except Exception as e:
                    logger.error(f"Failed to delete S3 file: {e}")

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
                        course=self.course,
                        url=url,
                        type=MemoryType.DOCUMENT,
                        name=name
                    )
        
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    def add_pdf_memory(self, s3_key: str, name: str) -> Memory: 
        """
        Process a PDF from S3 storage and store its contents with vector embeddings
        """
        logger.info(f"Processing PDF from S3: {s3_key}")

        memory = Memory.objects.create(
            url=s3_key,
            type=MemoryType.DOCUMENT,
            course=self.course,
            name=name  
        )

        try:
            # Download file from S3 to temporary location for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file_path = temp_file.name
                
            try:
                self.storage_service.download_file(s3_key, temp_file_path)
                
                if not os.path.exists(temp_file_path):
                    raise ValueError(f"File not found after download from S3: {s3_key}")
                
                logger.info(f"Processing PDF from temporary path: {temp_file_path}")

                # Process the PDF from temporary location
                documents = process_pdf(temp_file_path)

                if not documents:
                    logger.warning(f"No text content extracted from PDF: {temp_file_path}")
                    raise ValueError(f"No text content extracted from PDF: {name}")

                logger.info(f"Extracted {len(documents)} chunks from PDF")

                # Generate embeddings
                embeddings_response = gemini_client.models.embed_content(
                    model="gemini-embedding-exp-03-07",
                    contents=documents
                )

                embeddings_list = [embedding.values for embedding in embeddings_response.embeddings]
                document_instances = [
                    Document(
                        id=uuid.uuid4(),
                        content=doc_content,
                        embedding=embedding,
                        memory=memory
                    )
                    for doc_content, embedding in zip(documents, embeddings_list)
                ]

                Document.objects.bulk_create(
                    document_instances,
                    batch_size=1000 
                )
                
                logger.info(f"Successfully processed PDF: {name} with {len(document_instances)} chunks")
                memory.save()
                return memory
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            memory.delete()
            raise e
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            memory.delete()
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def upload_file(self, file, name: str) -> str:
        """
        Upload a file to S3 storage and return the S3 key
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create course-specific directory
            course_dir = f"course_{self.course.id}"
            
            # Save file to S3
            s3_key = self.storage_service.save_file(
                file, 
                subdirectory=course_dir, 
                filename=unique_filename,
                content_type=file.content_type
            )
            
            logger.info(f"File uploaded to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")

    def categorize_uploaded_document(self, memory: Memory):
        try:
            documents = Document.objects.filter(memory=memory)
            if not documents.exists():
                return
            
            sample_content = documents.first().content[:2000]
            
            categorization_prompt = f"""
            Analyze this document content and categorize it. What type of information does this contain?
            
            Content: {sample_content}
            
            Categories:
            - COURSE_PROFILE: About course, syllabus, objectives
            - MATERIAL: Study material, notes
            - POLICIES: Course policies, procedures
            - FAQ: Frequently asked questions
            - TRAINING: Training materials, guidelines
            - OTHER: Other type of content
            
            Respond with just the category name.
            """
            
            # Commented out Gemini - using Groq instead
            # response = gemini_client.models.generate_content(
            #     model="gemini-2.5-pro",
            #     contents=[categorization_prompt]
            # )
            # category = response.text.strip()
            
            # Use Groq for categorization
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": categorization_prompt}],
                temperature=0.3,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            logger.info(f"Document categorized as: {category}")
            
        except Exception as e:
            logger.error(f"Error categorizing document: {e}")