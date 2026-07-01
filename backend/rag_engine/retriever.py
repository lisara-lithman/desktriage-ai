import os
import chromadb
from chromadb.utils import embedding_functions
from rag_engine.config import logger, DB_PATH, EMBEDDING_MODEL_NAME, DISTANCE_THRESHOLD

# Singleton references
_chroma_client = None
_chroma_collection = None

def _get_collection():
    """Lazily initializes and returns the ChromaDB collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    try:
        # Check if the database directory exists
        if not os.path.exists(DB_PATH):
            logger.warning(f"⚠️ Chroma DB directory '{DB_PATH}' not found. Skipping retrieval.")
            return None
            
        _chroma_client = chromadb.PersistentClient(path=DB_PATH)
        embedder = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)
        
        # Verify collection exists in the database
        _chroma_collection = _chroma_client.get_collection(
            name="nexus_sops",
            embedding_function=embedder
        )
        logger.info("✅ ChromaDB retriever connection established successfully.")
        return _chroma_collection
    except Exception as e:
        logger.error(f"⚠️ Failed to connect to ChromaDB collection: {e}")
        return None

def retrieve_context(query: str, n_results: int = 2, distance_threshold: float = DISTANCE_THRESHOLD) -> dict:
    """
    Queries ChromaDB for similar document chunks.
    Filters results by distance_threshold to reject irrelevant chunks.
    
    Returns:
        dict: A dictionary containing:
            - 'context' (str): Concat of retrieved chunks, or empty string on failure/no-match.
            - 'sources' (list): List of sources matching the retrieved chunks.
    """
    fallback_result = {"context": "", "sources": []}
    
    if not query.strip():
        return fallback_result

    collection = _get_collection()
    if collection is None:
        return fallback_result

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return fallback_result
            
        documents = results["documents"][0]
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(documents)
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        
        filtered_docs = []
        filtered_sources = []
        
        for doc, dist, meta in zip(documents, distances, metadatas):
            if distance_threshold is None or dist <= distance_threshold:
                filtered_docs.append(doc)
                filtered_sources.append(meta.get("source", "Unknown"))
            else:
                logger.info(f"⏭️ Skipping chunk with distance {dist:.4f} (exceeds threshold {distance_threshold})")
        
        if filtered_docs:
            logger.info(f"📚 Retrieved {len(filtered_docs)} relevant context chunks (filtered from {len(documents)} total).")
            for idx, source in enumerate(filtered_sources):
                logger.info(f"   Chunk {idx} source: {source}")
        else:
            logger.info(f"⏭️ No context chunks met the distance threshold of {distance_threshold}.")
            
        return {
            "context": "\n\n".join(filtered_docs),
            "sources": filtered_sources
        }
    except Exception as e:
        logger.error(f"⚠️ Error querying ChromaDB retriever: {e}")
        return fallback_result

