"""
seed_admin.py — Run once to create/fix the master admin and all department admins.
Usage (from the backend/ directory with venv active):
    python seed_admin.py
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bcrypt import hashpw, gensalt
from dotenv import load_dotenv

# Load configuration values from the local environment block
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("🚨 MONGODB_URI configuration entry missing from your .env file!")

# Initialize the Non-Blocking Mongo Driver Client
client = AsyncIOMotorClient(MONGODB_URI)
db = client.desktriage_database

# Define the matrix of all enterprise administrators
ADMIN_PROFILES = [
    {
        "email": "admin@company.com",
        "password": "MasterAdminPassword2026!",
        "first_name": "Master",
        "last_name": "Admin",
        "username": "master_admin",
        "role": "admin_global",
        "department": "Global_Admin"
    },
    {
        "email": "it_admin@company.com",
        "password": "ITAdminPassword2026!",
        "first_name": "Tech",
        "last_name": "Lead",
        "username": "it_admin",
        "role": "admin_dept",
        "department": "IT_Support"
    },
    {
        "email": "hr_admin@company.com",
        "password": "HRAdminPassword2026!",
        "first_name": "People",
        "last_name": "Manager",
        "username": "hr_admin",
        "role": "admin_dept",
        "department": "HR_Operations"
    },
    {
        "email": "finance_admin@company.com",
        "password": "FinanceAdminPassword2026!",
        "first_name": "Billing",
        "last_name": "Director",
        "username": "finance_admin",
        "role": "admin_dept",
        "department": "Corporate_Finance"
    }
]

async def seed():
    print("⏳ Beginning database initialization and multi-department admin seeding...\n")

    for admin in ADMIN_PROFILES:
        # Securely hash the plain text password for each user
        hashed = hashpw(admin["password"].encode("utf-8"), gensalt()).decode("utf-8")

        # Upsert: Create the document if the email doesn't exist, update it if it does
        result = await db.users.update_one(
            {"email": admin["email"]},
            {
                "$set": {
                    "first_name": admin["first_name"],
                    "last_name": admin["last_name"],
                    "username": admin["username"],
                    "email": admin["email"],
                    "password_hash": hashed,
                    "phone_number": None,
                    "role": admin["role"],
                    "department": admin["department"]
                }
            },
            upsert=True,
        )

        if result.upserted_id:
            print(f"✅ CREATED [{admin['department']}]: {admin['email']}")
        else:
            print(f"🔄 UPDATED [{admin['department']}]: {admin['email']}")

    print("\n🎉 All department administrative accounts have been successfully seeded!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
