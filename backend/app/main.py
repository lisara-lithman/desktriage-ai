# backend/app/main.py
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import db
from app.routes.auth_routes   import router as auth_router
from app.routes.ticket_routes import router as ticket_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan: load the AI model once before accepting any requests ────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    - Startup:  load the fine-tuned MLX model into memory (warm-up included).
    - Shutdown: nothing special required for MLX (memory freed by OS).
    """
    logger.info("🚀 DeskTriage AI backend starting up…")
    try:
        from app.services import ai_service
        ai_service.load_model()
    except Exception as exc:
        logger.error(f"❌ Model load failed during startup: {exc}")
        logger.warning("⚠️  Continuing without AI — fallback values will be used.")

    yield  # Server is live and serving requests

    logger.info("🛑 DeskTriage AI backend shutting down.")


# 1. Initialize the core FastAPI framework application engine
app = FastAPI(
    title="DeskTriage AI Backend Core",
    description="Asynchronous Operations Ingestion & Authentication Engine with AI Triage",
    version="2.0.0",
    lifespan=lifespan,
)

# 2. Configure Cross-Origin Resource Sharing (CORS) Security Guardrails
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Routing Layers
app.include_router(auth_router)
app.include_router(ticket_router)

# 4. System Integrity Health Verification Endpoint
@app.get("/api/health", tags=["System Utility"])
async def health_check():
    from app.services import ai_service
    model_status = "loaded" if ai_service._model is not None else "not_loaded"
    try:
        await db.command("ping")
        return {
            "status":   "healthy",
            "database": "connected",
            "ai_model": model_status,
        }
    except Exception as error_payload:
        return {
            "status": "unhealthy",
            "reason": str(error_payload),
            "ai_model": model_status,
        }
