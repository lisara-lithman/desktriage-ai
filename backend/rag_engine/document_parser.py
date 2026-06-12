import hashlib
import re
import PyPDF2
from rag_engine.config import logger

def get_hash(filepath: str) -> str:
    """Creates a unique MD5 fingerprint for a file to prevent duplicate processing."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
    except Exception as e:
        logger.error(f"Failed to calculate hash for {filepath}: {e}")
        raise
    return hasher.hexdigest()

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from a PDF using PyPDF2."""
    raw_text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    raw_text += extracted + "\n\n"
    except Exception as e:
        logger.error(f"Error reading PDF file {pdf_path}: {e}")
        return ""
    return raw_text

def extract_text_from_txt_or_md(filepath: str) -> str:
    """Extracts raw text from plain text or markdown files."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading text file {filepath}: {e}")
        return ""

def clean_text(raw_text: str) -> str:
    """Normalizes layout formatting, removes loose spacing, and preserves paragraph structure."""
    if not raw_text.strip():
        return ""
    
    # 1. Temporarily mark paragraph boundaries
    text = re.sub(r'\n\s*\n', '==PARAGRAPH_BOUNDARY==', raw_text)
    # 2. Flatten single/broken lines inside paragraphs to spaces
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # 3. Clean up loose/multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    # 4. Restore structural boundaries
    text = text.replace('==PARAGRAPH_BOUNDARY==', '\n\n')
    return text.strip()
