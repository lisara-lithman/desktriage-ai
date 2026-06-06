from pydantic import BaseModel, Field
from typing import Optional

class TicketCreateSchema(BaseModel):
    title:       str = Field(..., example="Cannot connect to corporate VPN")
    description: str = Field(..., example="My access token expired this morning and I am locked out.")
    department:  str = Field(..., example="IT_Support")   # Chosen from frontend dropdown
    priority:    str = Field(..., example="High")          # Chosen from frontend dropdown


class AdminReplySchema(BaseModel):
    admin_reply: str = Field(..., example="We have reset your VPN token. Please try again.")
    status:      str = Field(..., example="Resolved")  # In_Progress | Resolved | Closed