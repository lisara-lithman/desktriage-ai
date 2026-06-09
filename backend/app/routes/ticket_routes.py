"""
ticket_routes.py — Full ticket lifecycle routes with AI triage integration.

ROUTE ORDER MATTERS in FastAPI — static paths must be declared before wildcard paths.

Routes (in declaration order):
  POST /api/tickets/submit              — Employee submits a ticket (AI runs in background)
  GET  /api/tickets/my                  — Employee fetches their own tickets
  GET  /api/tickets/admin/all           — admin_global sees ALL tickets
  GET  /api/tickets/admin/dept          — admin_dept sees tickets for their department only
  GET  /api/tickets/{ticket_id}         — Fetch a single ticket by ID (MUST be after static routes)
  POST /api/tickets/{ticket_id}/reply   — Admin confirms reply and updates ticket status
"""

from bson import ObjectId
from datetime import datetime, timezone
from fastapi import APIRouter, status, HTTPException, Depends, BackgroundTasks

from app.database.connection import db
from app.models.ticket_model import TicketCreateSchema, AdminReplySchema
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


# ── Helper: convert a MongoDB document to a JSON-safe dict ───────────────────
def serialize_ticket(ticket: dict) -> dict:
    ticket["_id"] = str(ticket["_id"])
    return ticket


# ── Background Task: run AI inference and update the ticket ──────────────────
async def run_ai_triage(ticket_id: str, title: str, description: str):
    """
    Runs after the submit response is already sent to the employee.
    Calls the AI service, then updates the ticket document with the results.
    """
    from app.services import ai_service

    try:
        result = ai_service.generate_triage(title, description)

        new_status = "Pending_Admin_Review"
        update_fields = {
            "department":    result["department"],
            "priority":      result["priority"],
            "ai_draft_reply": result["ai_draft_reply"],
            "ai_department": result["department"],   # audit trail copy
            "ai_priority":   result["priority"],     # audit trail copy
            "ai_failed":     result.get("ai_failed", False),
            "status":        new_status,
            "updated_at":    datetime.now(timezone.utc).isoformat(),
        }

        await db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": update_fields}
        )

    except Exception as exc:
        # Even on failure, move ticket out of AI_Processing so it doesn't get stuck
        await db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": {
                "status":     "Pending_Admin_Review",
                "ai_failed":  True,
                "department": "IT_Support",
                "priority":   "Medium",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }}
        )


# ─────────────────────────────────────────────────────────────────────────────
# USER ROUTE: Submit a new ticket
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_ticket(
    ticket_in:        TicketCreateSchema,
    background_tasks: BackgroundTasks,
    current_user:     dict = Depends(get_current_user)
):
    """
    Authenticated employee submits a support ticket.
    - Ticket is saved immediately with status 'AI_Processing'.
    - AI inference runs in a BackgroundTask (non-blocking).
    - Employee gets an instant response; AI draft appears within ~30s.
    """
    now = datetime.now(timezone.utc).isoformat()

    new_ticket = {
        "employee_username": current_user["username"],
        "employee_email":    current_user["email"],
        "title":             ticket_in.title,
        "description":       ticket_in.description,
        # AI will populate these — placeholders until background task completes
        "department":        "Pending",
        "priority":          "Pending",
        "ai_draft_reply":    "",
        "ai_department":     "",
        "ai_priority":       "",
        "ai_failed":         False,
        "status":            "AI_Processing",
        "admin_reply":       "",
        "replied_by":        "",
        "created_at":        now,
        "updated_at":        now,
    }

    result = await db.tickets.insert_one(new_ticket)
    ticket_id = str(result.inserted_id)

    # Queue the AI background task — runs after this response is sent
    background_tasks.add_task(
        run_ai_triage,
        ticket_id,
        ticket_in.title,
        ticket_in.description,
    )

    return {
        "success":   True,
        "message":   "Ticket submitted! Our AI is analyzing your issue now. You can track status in My Tickets.",
        "ticket_id": ticket_id,
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
# IMPORTANT: This must be declared BEFORE the wildcard /{ticket_id} route.
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
# IMPORTANT: This must be declared BEFORE the wildcard /{ticket_id} route.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/admin/dept")
async def get_dept_tickets(current_user: dict = Depends(require_admin)):
    """
    Department admin sees only tickets directed at their department.
    Also includes AI_Processing tickets (not yet classified) for visibility.
    Global admin calling this will also be scoped — use /admin/all instead.
    """
    dept = current_user.get("department")

    # Return tickets for this dept OR still being processed by AI
    cursor  = db.tickets.find({
        "$or": [
            {"department": dept},
            {"status": "AI_Processing"},
        ]
    }).sort("created_at", -1)

    tickets = [serialize_ticket(t) async for t in cursor]
    return {"success": True, "tickets": tickets, "department": dept}


# ─────────────────────────────────────────────────────────────────────────────
# SHARED ROUTE: Fetch a single ticket by ID
# IMPORTANT: Wildcard route — MUST be declared AFTER all static /admin/* routes.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id:    str,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch a single ticket by its ID.
    Used by the admin dashboard to poll for AI draft completion.
    - Employees can only access their own tickets.
    - Admins can access any ticket.
    """
    try:
        oid = ObjectId(ticket_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket ID format.")

    ticket = await db.tickets.find_one({"_id": oid})
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    # Access control: employee can only see their own ticket
    role = current_user.get("role", "user")
    if role == "user" and ticket.get("employee_username") != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return {"success": True, "ticket": serialize_ticket(ticket)}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ROUTE: Confirm AI draft and send reply to employee
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{ticket_id}/reply", status_code=status.HTTP_200_OK)
async def reply_to_ticket(
    ticket_id:    str,
    reply_in:     AdminReplySchema,
    current_user: dict = Depends(require_admin)
):
    """
    Admin confirms (and optionally edits) the AI draft reply, then sends it.
    The confirmed reply is stored in admin_reply — separate from ai_draft_reply.
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
        ticket_dept = ticket.get("department")
        admin_dept  = current_user.get("department")
        if ticket_dept not in ("Pending", "AI_Processing") and ticket_dept != admin_dept:
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
        "message": f"Reply confirmed and sent. Ticket status updated to '{reply_in.status}'."
    }