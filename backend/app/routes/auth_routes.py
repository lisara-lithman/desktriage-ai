from fastapi import APIRouter, HTTPException, status
from app.database.connection import db
from app.models.user_model import UserRegisterSchema, UserLoginSchema
from app.auth.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register")
async def register(user_data: UserRegisterSchema):
    # 1. Check if the email is already registered in the database
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 2. Scramble the raw text password string
    scrambled_password = hash_password(user_data.password)

    # 3. Create a new user document
    new_user = {
        "first_name":    user_data.first_name,
        "last_name":     user_data.last_name,
        "username":      user_data.username,
        "email":         user_data.email,
        "password_hash": scrambled_password,
        "phone_number":  user_data.phone_number,
        "role":          "user",
        "department":    None,
    }

    # 4. Insert the new user document into the database
    result = await db.users.insert_one(new_user)
    if result.inserted_id:
        return {"message": "User registered successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")


@router.post("/login")
async def login(login_data: UserLoginSchema):
    # 1. Search for the user in the database by email
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 2. Verify the provided password against the stored hashed password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 3. Create JWT token — include username, role, email, and department
    token = create_access_token({
        "username":   user["username"],
        "role":       user["role"],
        "email":      user["email"],
        "department": user.get("department"),
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user["role"],
        "username":     user["username"],
        "email":        user["email"],
        "department":   user.get("department"),
    }
