# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import db
from app.routes.auth_routes   import router as auth_router
from app.routes.ticket_routes import router as ticket_router

# 1. Initialize the core FastAPI framework application engine
app = FastAPI(
    title="DeskTriage AI Backend Core",
    description="Asynchronous Operations Ingestion & Authentication Engine",
    version="1.0.0"
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
    try:
        await db.command("ping")
        return {
            "status":   "healthy",
            "database": "successfully connected to cloud storage tier"
        }
    except Exception as error_payload:
        return {
            "status": "unhealthy",
            "reason": str(error_payload)
        }
