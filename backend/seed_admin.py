"""
seed_admin.py — Run once to create/fix the admin user with a bcrypt-hashed password.
Usage (from the backend/ directory with venv active):
    python seed_admin.py
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bcrypt import hashpw, gensalt
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI not found in .env")

client = AsyncIOMotorClient(MONGODB_URI)
db = client.desktriage_database

ADMIN_EMAIL    = "admin@company.com"
ADMIN_PASSWORD = "MasterAdminPassword2026"

async def seed():
    hashed = hashpw(ADMIN_PASSWORD.encode("utf-8"), gensalt()).decode("utf-8")

    result = await db.users.update_one(
        {"email": ADMIN_EMAIL},
        {
            "$set": {
                "first_name":     "Master",
                "last_name":      "Admin",
                "username":       "master_admin",
                "email":          ADMIN_EMAIL,
                "password_hash":  hashed,
                "phone_number":   None,
                "role":           "admin",
            }
        },
        upsert=True,
    )

    if result.upserted_id:
        print(f"✅  Admin user CREATED with email: {ADMIN_EMAIL}")
    else:
        print(f"✅  Admin user UPDATED (password re-hashed) for email: {ADMIN_EMAIL}")

    client.close()

asyncio.run(seed())
