import logging
import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger("__name__")

def process_pdf(pdf_path: str):
    """Process pdf with improved memory management."""
    try:
        doc = fitz.open(pdf_path)
        documents = []
        
        # Initialize text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            length_function=len
        )
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            if text.strip():
                # Split page text into chunks
                chunks = text_splitter.split_text(text)
                for chunk in chunks:
                    if chunk.strip():
                        documents.append(chunk.strip())
        
        doc.close()
        return documents
            
    except Exception as e:
        logger.error(f"Error processing PDF with PyMuPDF: {e}")
        return []
