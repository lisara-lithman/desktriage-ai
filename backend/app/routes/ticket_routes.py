"""
ticket_routes.py — Full ticket lifecycle routes.

Routes:
  POST /api/tickets/submit           — Authenticated user submits a ticket
  GET  /api/tickets/my               — User fetches their own tickets
  GET  /api/tickets/admin/all        — admin_global sees ALL tickets
  GET  /api/tickets/admin/dept       — admin_dept sees tickets for their department only
  POST /api/tickets/{ticket_id}/reply — Admin posts a reply and updates status
"""

from bson import ObjectId
from datetime import datetime, timezone
from fastapi import APIRouter, status, HTTPException, Depends

from app.database.connection import db
from app.models.ticket_model import TicketCreateSchema, AdminReplySchema
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


# ── Helper: convert a MongoDB document to a JSON-safe dict ────────────────────
def serialize_ticket(ticket: dict) -> dict:
    ticket["_id"] = str(ticket["_id"])
    return ticket


# ─────────────────────────────────────────────────────────────────────────────
# USER ROUTE: Submit a new ticket
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_ticket(
    ticket_in: TicketCreateSchema,
    current_user: dict = Depends(get_current_user)
):
    """
    Authenticated employee submits a support ticket.
    Identity is pulled from the JWT — the user cannot spoof who they are.
    Ticket is routed to the matching department admin AND the global admin.
    """
    now = datetime.now(timezone.utc).isoformat()

    new_ticket = {
        "employee_username": current_user["username"],
        "employee_email":    current_user["email"],
        "title":             ticket_in.title,
        "description":       ticket_in.description,
        "department":        ticket_in.department,
        "priority":          ticket_in.priority,
        "status":            "Pending_Admin_Review",
        "admin_reply":       "",
        "replied_by":        "",
        "created_at":        now,
        "updated_at":        now,
    }

    result = await db.tickets.insert_one(new_ticket)

    return {
        "success":   True,
        "message":   "Ticket submitted successfully. Your admin has been notified.",
        "ticket_id": str(result.inserted_id),
    }


# ─────────────────────────────────────────────────────────────────────────────
# USER ROUTE: Fetch the logged-in user's own tickets
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/my")
async def get_my_tickets(current_user: dict = Depends(get_current_user)):
    """
    Returns all tickets submitted by the currently logged-in employee.
    Newest tickets are returned first.
    """
    cursor  = db.tickets.find(
        {"employee_username": current_user["username"]}
    ).sort("created_at", -1)

    tickets = [serialize_ticket(t) async for t in cursor]
    return {"success": True, "tickets": tickets}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ROUTE: Global admin — fetch ALL tickets across all departments
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/admin/all")
async def get_all_tickets(current_user: dict = Depends(require_admin)):
    """
    Global admin only. Returns every ticket in the system, newest first.
    """
    if current_user.get("role") != "admin_global":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Global Admin can access all tickets."
        )

    cursor  = db.tickets.find({}).sort("created_at", -1)
    tickets = [serialize_ticket(t) async for t in cursor]
    return {"success": True, "tickets": tickets}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ROUTE: Department admin — fetch only their department's tickets
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/admin/dept")
async def get_dept_tickets(current_user: dict = Depends(require_admin)):
    """
    Department admin sees only tickets directed at their department.
    Global admin calling this will also be scoped — use /admin/all instead.
    """
    dept    = current_user.get("department")
    cursor  = db.tickets.find({"department": dept}).sort("created_at", -1)
    tickets = [serialize_ticket(t) async for t in cursor]
    return {"success": True, "tickets": tickets, "department": dept}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ROUTE: Post a reply to a specific ticket
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{ticket_id}/reply", status_code=status.HTTP_200_OK)
async def reply_to_ticket(
    ticket_id:    str,
    reply_in:     AdminReplySchema,
    current_user: dict = Depends(require_admin)
):
    """
    Admin submits a reply and optionally changes the ticket status.
    The reply is stored inside the ticket document, visible to the employee.
    """
    # Validate the ticket ID format before querying
    try:
        oid = ObjectId(ticket_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID format."
        )

    # Confirm the ticket actually exists
    ticket = await db.tickets.find_one({"_id": oid})
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )

    # Department admin can only reply to their own department's tickets
    if current_user.get("role") == "admin_dept":
        if ticket.get("department") != current_user.get("department"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reply to tickets in your own department."
            )

    now = datetime.now(timezone.utc).isoformat()

    await db.tickets.update_one(
        {"_id": oid},
        {
            "$set": {
                "admin_reply": reply_in.admin_reply,
                "status":      reply_in.status,
                "replied_by":  current_user["username"],
                "updated_at":  now,
            }
        }
    )

    return {
        "success": True,
        "message": f"Reply posted and ticket status updated to '{reply_in.status}'."
    }