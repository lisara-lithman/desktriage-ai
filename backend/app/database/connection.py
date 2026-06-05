import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 1. Look inside the hidden .env file and load the variables into your Mac's memory
load_dotenv()

# 2. Extract the connection string variable
MONGODB_URL = os.getenv("MONGODB_URI")

# 3. Establish an asynchronous pipeline connection to the MongoDB Atlas cloud cluster
client = AsyncIOMotorClient(MONGODB_URL)

# 4. Point to a database name. MongoDB will create it automatically if it doesn't exist!
db = client.desktriage_database