"""Comment routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, Comment, Ticket, User
from ..schemas import CommentCreate, CommentOut

router = APIRouter(tags=["comments"])


@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = Comment(
        ticket_id=ticket_id,
        author_id=current_user.id,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    activity = Activity(
        ticket_id=ticket_id,
        actor_id=current_user.id,
        kind="commented",
        detail="",
    )
    db.add(activity)
    db.commit()
    return comment


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Comment)
        .filter(Comment.ticket_id == ticket_id, Comment.is_deleted == False)  # noqa: E712
        .order_by(Comment.created_at)
        .all()
    )
