import os
import logging

# Setup standard logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rag_engine")

# --- PATH CONFIGURATIONS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Location where source documents to ingest are stored
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "knowledge_base"))

# Location where the persistent vector database is stored
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "chroma_db"))

# --- EMBEDDING CONFIGURATIONS ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
