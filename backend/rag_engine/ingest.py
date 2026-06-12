import sys
import os
import argparse
from typing import Dict, Set

# Add the backend directory to sys.path to allow running this script from anywhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

from rag_engine.config import logger, DATA_DIR, DB_PATH, EMBEDDING_MODEL_NAME
from rag_engine.document_parser import get_hash, extract_text_from_pdf, extract_text_from_txt_or_md, clean_text
from rag_engine.chunker import hybrid_chunker

# Explicitly configure embedding function
embedder = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)

def run_ingestion(reset_db: bool = False):
    """Builds and updates the Vector Database with modern file parsing and incremental ingestion."""
    logger.info(f"🚀 Starting Knowledge Base Ingestion using {EMBEDDING_MODEL_NAME}...")
    
    if not os.path.exists(DATA_DIR):
        logger.error(f"❌ Error: Target data directory '{DATA_DIR}' folder not found.")
        return

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=DB_PATH)
    
    if reset_db:
        logger.info("🗑️ Resetting database collection 'nexus_sops'...")
        try:
            client.delete_collection("nexus_sops")
        except Exception:
            pass # Collection might not exist yet

    collection = client.get_or_create_collection(
        name="nexus_sops", 
        embedding_function=embedder
    )
    
    # Fetch existing documents to allow incremental ingestion & deletion of deleted files
    existing_docs = collection.get()
    existing_ids = set(existing_docs.get("ids", []))
    
    # Map sources currently in DB to their hashes
    db_sources_to_hashes: Dict[str, Set[str]] = {}
    for idx, doc_id in enumerate(existing_docs.get("ids", [])):
        metadata = existing_docs.get("metadatas", [])[idx]
        if metadata and "source" in metadata:
            source_file = metadata["source"]
            parts = doc_id.split("_")
            if len(parts) > 1:
                f_hash = parts[0]
                db_sources_to_hashes.setdefault(source_file, set()).add(f_hash)

    docs_to_save, metadatas_to_save, ids_to_save = [], [], []
    active_files = set()

    # Scan directories for files
    all_files = [f for f in os.listdir(DATA_DIR) if not f.startswith(".")]
    
    for filename in tqdm(all_files, desc="Scanning files"):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
            
        file_lower = filename.lower()
        is_pdf = file_lower.endswith(".pdf")
        is_text = file_lower.endswith((".txt", ".md"))
        
        if not (is_pdf or is_text):
            continue
            
        active_files.add(filename)
        
        try:
            file_hash = get_hash(filepath)
        except Exception:
            continue
            
        # Incremental check: Skip if this exact file hash is already processed
        first_chunk_id = f"{file_hash}_0"
        if first_chunk_id in existing_ids:
            logger.debug(f"Skip: {filename} (already up-to-date).")
            continue
            
        # If the file has changed (hash changed but filename exists in DB), delete obsolete chunks
        if filename in db_sources_to_hashes:
            logger.info(f"🔄 File {filename} modified. Removing stale vector chunks...")
            collection.delete(where={"source": filename})
            
        logger.info(f"📄 Processing: {filename}...")
        
        if is_pdf:
            raw_text = extract_text_from_pdf(filepath)
        else:
            raw_text = extract_text_from_txt_or_md(filepath)
            
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text:
            logger.warning(f"⚠️ Warning: No readable text extracted from {filename} (might be empty/scanned).")
            continue
            
        chunks = hybrid_chunker(cleaned_text)
        
        for i, chunk in enumerate(chunks):
            ids_to_save.append(f"{file_hash}_{i}")
            docs_to_save.append(chunk)
            metadatas_to_save.append({"source": filename, "hash": file_hash})

    # Cleanup stale vectors for files that were deleted from the knowledge base directory
    for db_source in db_sources_to_hashes.keys():
        if db_source not in active_files:
            logger.info(f"🗑️ File {db_source} deleted from source. Purging associated vectors...")
            collection.delete(where={"source": db_source})

    if docs_to_save:
        logger.info(f"⚙️ Vectorizing {len(docs_to_save)} new/updated chunks and saving to ChromaDB...")
        
        # Batching optimization
        BATCH_SIZE = 2000
        for i in range(0, len(docs_to_save), BATCH_SIZE):
            end_idx = i + BATCH_SIZE
            collection.upsert(  # Safe upsert prevents duplicate crash
                ids=ids_to_save[i:end_idx],
                documents=docs_to_save[i:end_idx],
                metadatas=metadatas_to_save[i:end_idx]
            )
        logger.info("🎉 Database successfully updated!")
    else:
        logger.info("✅ Database is up to date.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest docs into ChromaDB.")
    parser.add_argument("--reset", action="store_true", help="Reset DB collection before starting.")
    args = parser.parse_args()
    
    run_ingestion(reset_db=args.reset)