from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional


class UserRegisterSchema(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    phone_number: Optional[str] = None

    # This validator checks fields AFTER they are individually validated
    @model_validator(mode="after")
    def verify_passwords_match(self) -> "UserRegisterSchema":
        pw = self.password
        confirm_pw = self.confirm_password
        
        if pw != confirm_pw:
            raise ValueError("Passwords do not match")
            
        return self


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

