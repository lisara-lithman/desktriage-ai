# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import db
from app.routes.auth_routes import router as auth_router

# 1. Initialize the core FastAPI framework application engine
app = FastAPI(
    title="DeskTriage AI Backend Core",
    description="Asynchronous Operations Ingestion & Authentication Engine",
    version="1.0.0"
)

# 2. Configure Cross-Origin Resource Sharing (CORS) Security Guardrails
# This explicitly tells your computer that our React frontend UI (running on port 5173)
# has authenticated authority to pass network API requests to this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Security Routing Layers
# This attaches our /register and /login endpoints smoothly to the server engine.
app.include_router(auth_router)

# 4. System Integrity Health Verification Endpoint
@app.get("/api/health", tags=["System Utility"])
async def health_check():
    try:
        # Ping the remote MongoDB Atlas cluster to check database accessibility
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "successfully connected to cloud storage tier"
        }
    except Exception as error_payload:
        return {
            "status": "unhealthy",
            "reason": str(error_payload)
        }


