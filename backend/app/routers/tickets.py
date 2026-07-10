"""Ticket routes.

This module holds most of the ticket lifecycle logic.
"""
from datetime import datetime, timedelta
# from datetime import timezone  # PROPOSED FIX: needed for the tz-aware-then-stripped helper (see models.py)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
# from sqlalchemy import update  # PROPOSED FIX: needed for the atomic sequence helper below

from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, Comment, Membership, Ticket, User, Workspace
# from ..models import _utcnow_naive  # PROPOSED FIX: shared naive-UTC helper
from ..notifications import send_notification
# from ..notifications import enqueue_notification  # PROPOSED FIX: queue-based, DB-backed delivery
from ..schemas import TicketCreate, TicketOut, TicketUpdate

router = APIRouter(tags=["tickets"])


def _require_membership(db: Session, user: User, workspace_id: int) -> None:
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user.id,
            Membership.workspace_id == workspace_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

# PROPOSED FIX: replaces the `COUNT(*) WHERE is_deleted == False` identifier
# generation used in create_ticket and bulk_create_tickets, which caused two
# tickets to end up as ENG-7: soft-deleting a ticket shrinks the active
# count, so a later create can recompute a number that's already taken by
# an existing, non-deleted ticket. It also raced under concurrent requests,
# since two callers could read the same count before either committed.
#
# This does a single atomic `UPDATE ... SET ticket_sequence = ticket_sequence
# + 1 RETURNING ticket_sequence`, so the counter only ever moves forward and
# two concurrent callers cannot get the same value back. Requires the
# `ticket_sequence` column on Workspace (see models.py proposed fix).
#
# def _next_ticket_number(db: Session, workspace_id: int) -> int:
#     result = db.execute(
#         update(Workspace)
#         .where(Workspace.id == workspace_id)
#         .values(ticket_sequence=Workspace.ticket_sequence + 1)
#         .returning(Workspace.ticket_sequence)
#     )
#     db.commit()
#     return result.scalar_one()


@router.post("/workspaces/{workspace_id}/tickets", response_model=TicketOut)
# PROPOSED FIX: this is one of only two `async def` handlers in the whole
# router (the rest are plain `def`, which Starlette auto-threadpools). It
# has no real `await` anywhere and calls send_notification() below, which
# does a synchronous time.sleep(0.05) — that blocks this worker's entire
# event loop for 50ms per call since async handlers are NOT threadpooled.
# Dropping to plain `def` matches every other handler in this file and lets
# Starlette run it (and its blocking DB/notification calls) in a threadpool
# instead of on the event loop.
# def create_ticket(
async def create_ticket(
    workspace_id: int,
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    _require_membership(db, current_user, workspace_id)

    # Next ticket number for this workspace.
    count = (
        db.query(Ticket)
        .filter(Ticket.workspace_id == workspace_id, Ticket.is_deleted == False)  # noqa: E712
        .count()
    )
    identifier = f"{ws.key}-{count + 1}"
    # PROPOSED FIX: replace the two lines above with an atomically
    # incremented, persistent counter that isn't affected by deletes or races.
    # identifier = f"{ws.key}-{_next_ticket_number(db, workspace_id)}"

    ticket = Ticket(
        workspace_id=workspace_id,
        identifier=identifier,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        creator_id=current_user.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Record the creation in the activity feed.
    activity = Activity(
        ticket_id=ticket.id,
        actor_id=current_user.id,
        kind="created",
        detail=identifier,
    )
    db.add(activity)
    db.commit()

    if payload.assignee_id:
        send_notification(payload.assignee_id, f"You were assigned {identifier}")
        # PROPOSED FIX: was a blocking call (time.sleep) made directly in
        # the request path, on an in-memory outbox that's broken across
        # workers. This does a fast DB insert instead and hands off actual
        # delivery to the background queue worker (see notifications.py).
        # enqueue_notification(db, payload.assignee_id, f"You were assigned {identifier}")

    return ticket


@router.post("/workspaces/{workspace_id}/tickets/bulk", response_model=list[TicketOut])
# PROPOSED FIX: same reasoning as create_ticket above — no real `await`
# here either, just N sequential sync DB round trips held on the event loop
# for the whole request instead of being threadpooled.
# def bulk_create_tickets(
async def bulk_create_tickets(
    workspace_id: int,
    payloads: list[TicketCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    _require_membership(db, current_user, workspace_id)

    created = []
    for payload in payloads:
        count = (
            db.query(Ticket)
            .filter(Ticket.workspace_id == workspace_id, Ticket.is_deleted == False)  # noqa: E712
            .count()
        )
        identifier = f"{ws.key}-{count + 1}"
        # PROPOSED FIX: same reasoning as create_ticket above — this loop is
        # additionally its own race, since each iteration recomputes count
        # from a table that a concurrent request could also be inserting
        # into between this workspace's iterations.
        # identifier = f"{ws.key}-{_next_ticket_number(db, workspace_id)}"
        ticket = Ticket(
            workspace_id=workspace_id,
            identifier=identifier,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            assignee_id=payload.assignee_id,
            creator_id=current_user.id,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        created.append(ticket)
    return created


@router.get("/workspaces/{workspace_id}/tickets", response_model=list[TicketOut])
def list_tickets(
    workspace_id: int,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_membership(db, current_user, workspace_id)
    return (
        db.query(Ticket)
        .filter(Ticket.workspace_id == workspace_id, Ticket.is_deleted == False)  # noqa: E712
        .order_by(Ticket.created_at)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/tickets/search", response_model=list[TicketOut])
def search_tickets(
    q: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Simple title/description search.
    sql = text(
        "SELECT * FROM tickets "
        f"WHERE title LIKE '%{q}%' OR description LIKE '%{q}%' "
        "ORDER BY created_at DESC"
    )
    rows = db.execute(sql).fetchall()
    return [Ticket(**dict(row._mapping)) for row in rows]

# PROPOSED FIX: was SQL injection (q spliced into raw SQL) + no membership
# check at all (leaked tickets across every workspace to any logged-in
# user). Rewritten on the ORM with bound params and scoped to a workspace
# the caller is a member of. Note this adds a required `workspace_id` query
# param, which is an API change worth confirming before activating.
#
# @router.get("/tickets/search", response_model=list[TicketOut])
# def search_tickets(
#     q: str,
#     workspace_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     _require_membership(db, current_user, workspace_id)
#     like = f"%{q}%"
#     return (
#         db.query(Ticket)
#         .filter(
#             Ticket.workspace_id == workspace_id,
#             Ticket.is_deleted == False,  # noqa: E712
#             (Ticket.title.ilike(like)) | (Ticket.description.ilike(like)),
#         )
#         .order_by(Ticket.created_at.desc())
#         .all()
#     )


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

# PROPOSED FIX: was IDOR — any authenticated user could fetch any ticket by
# id regardless of workspace membership.
#
# def get_ticket(
#     ticket_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
#     if not ticket:
#         raise HTTPException(status_code=404, detail="Ticket not found")
#     _require_membership(db, current_user, ticket.workspace_id)
#     return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ticket, field, value)

    if data.get("status") == "done":
        ticket.closed_at = datetime.utcnow()
        # ticket.closed_at = _utcnow_naive()  # PROPOSED FIX

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

# PROPOSED FIX: was IDOR (no membership check) + mass assignment (payload
# could set workspace_id, creator_id, is_deleted, id, etc. because
# TicketUpdate used extra="allow" with no fields defined). This half of the
# fix adds the membership check; the field whitelist is fixed at the schema
# layer in schemas.py (see TicketUpdate proposed fix there) so pydantic
# rejects unknown fields before we ever get here.
#
# def update_ticket(
#     ticket_id: int,
#     payload: TicketUpdate,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
#     if not ticket:
#         raise HTTPException(status_code=404, detail="Ticket not found")
#     _require_membership(db, current_user, ticket.workspace_id)
#
#     data = payload.model_dump(exclude_unset=True)
#     for field, value in data.items():
#         setattr(ticket, field, value)
#
#     if data.get("status") == "done":
#         ticket.closed_at = datetime.utcnow()
#
#     db.add(ticket)
#     db.commit()
#     db.refresh(ticket)
#     return ticket


@router.delete("/tickets/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.is_deleted = True
    db.add(ticket)
    db.commit()
    return {"deleted": True}

# PROPOSED FIX: was IDOR — any authenticated user could soft-delete any
# ticket in any workspace by id.
#
# def delete_ticket(
#     ticket_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
#     if not ticket:
#         raise HTTPException(status_code=404, detail="Ticket not found")
#     _require_membership(db, current_user, ticket.workspace_id)
#     ticket.is_deleted = True
#     db.add(ticket)
#     db.commit()
#     return {"deleted": True}


@router.get("/workspaces/{workspace_id}/stats")
def workspace_stats(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_membership(db, current_user, workspace_id)
    tickets = db.query(Ticket).filter(Ticket.workspace_id == workspace_id).all()

    open_count = 0
    total_comments = 0
    for ticket in tickets:
        if ticket.status == "open":
            open_count += 1
        total_comments += len(ticket.comments)

    week_ago = datetime.utcnow() - timedelta(days=7)
    # week_ago = _utcnow_naive() - timedelta(days=7)  # PROPOSED FIX
    recent = [t for t in tickets if t.created_at > week_ago]

    return {
        "total_tickets": len(tickets),
        "open_tickets": open_count,
        "total_comments": total_comments,
        "created_last_7_days": len(recent),
    }

# PROPOSED FIX: was counting soft-deleted tickets and soft-deleted comments,
# so the stats page never matched what list_tickets/list_comments actually
# show. Applies the same is_deleted filters those endpoints already use.
# Also, "open_count" only matched status == "open", undercounting tickets
# in any other non-terminal status (e.g. "in_progress", or any future
# intermediate status like "verify") that a user would still consider
# active. Inverted to count anything NOT in the terminal set (done,
# canceled) instead of enumerating active statuses one-by-one, so new
# intermediate statuses are picked up automatically.
#
# TERMINAL_TICKET_STATUSES = {"done", "canceled"}
#
# @router.get("/workspaces/{workspace_id}/stats")
# def workspace_stats(
#     workspace_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     _require_membership(db, current_user, workspace_id)
#     tickets = (
#         db.query(Ticket)
#         .filter(Ticket.workspace_id == workspace_id, Ticket.is_deleted == False)  # noqa: E712
#         .all()
#     )
#
#     open_count = 0
#     total_comments = 0
#     for ticket in tickets:
#         if ticket.status not in TERMINAL_TICKET_STATUSES:
#             open_count += 1
#         total_comments += sum(1 for c in ticket.comments if not c.is_deleted)
#
#     week_ago = datetime.utcnow() - timedelta(days=7)
#     recent = [t for t in tickets if t.created_at > week_ago]
#
#     return {
#         "total_tickets": len(tickets),
#         "open_tickets": open_count,
#         "total_comments": total_comments,
#         "created_last_7_days": len(recent),
#     }
