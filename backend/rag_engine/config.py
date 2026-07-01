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

# Max allowed distance threshold for vector search results (using squared L2 distance).
# For normalized sentence-transformer embeddings:
#   - 0.0 = perfect match
#   - < 0.8 = strong semantic similarity
#   - > 0.85 = weak/irrelevant similarity
# Chunks with distance higher than this threshold will be discarded.
DISTANCE_THRESHOLD = 0.85

