"""Ticket routes.

This module holds most of the ticket lifecycle logic.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, Comment, Membership, Ticket, User, Workspace
from ..notifications import send_notification
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


@router.post("/workspaces/{workspace_id}/tickets", response_model=TicketOut)
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

    return ticket


@router.post("/workspaces/{workspace_id}/tickets/bulk", response_model=list[TicketOut])
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

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


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
    recent = [t for t in tickets if t.created_at > week_ago]

    return {
        "total_tickets": len(tickets),
        "open_tickets": open_count,
        "total_comments": total_comments,
        "created_last_7_days": len(recent),
    }
