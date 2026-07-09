"""Workspace routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Membership, User, Workspace
from ..schemas import WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = Workspace(name=payload.name, key=payload.key, owner_id=current_user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    membership = Membership(user_id=current_user.id, workspace_id=ws.id, role="admin")
    db.add(membership)
    db.commit()
    return ws


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(Membership).filter(Membership.user_id == current_user.id).all()
    )
    ws_ids = [m.workspace_id for m in memberships]
    return db.query(Workspace).filter(Workspace.id.in_(ws_ids)).all()


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()
    return {"deleted": True}
