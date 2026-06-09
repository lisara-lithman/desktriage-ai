from pydantic import BaseModel, Field
from typing import Optional


class TicketCreateSchema(BaseModel):
    """
    Schema for employee ticket submission.
    Department and priority are intentionally omitted — the AI model
    predicts them automatically from the title and description.
    """
    title:       str = Field(..., min_length=5,  max_length=200,  example="Cannot connect to corporate VPN")
    description: str = Field(..., min_length=10, max_length=5000, example="My access token expired this morning and I am locked out.")


class AdminReplySchema(BaseModel):
    """
    Schema for admin confirming and sending a reply to the employee.
    The admin may edit the AI-generated draft before confirming.
    """
    admin_reply: str = Field(..., min_length=1, example="We have reset your VPN token. Please try again.")
    status:      str = Field(..., example="Resolved")   # In_Progress | Resolved | Closed