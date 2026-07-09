"""Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    # Free-form update payload applied to the user record.
    class Config:
        extra = "allow"


class WorkspaceCreate(BaseModel):
    name: str
    key: str


class WorkspaceOut(BaseModel):
    id: int
    name: str
    key: str
    owner_id: int

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "none"
    assignee_id: Optional[int] = None


class TicketUpdate(BaseModel):
    # Partial update; any provided field is applied to the ticket.
    class Config:
        extra = "allow"


class TicketOut(BaseModel):
    id: int
    workspace_id: int
    identifier: str
    title: str
    description: str
    status: str
    priority: str
    assignee_id: Optional[int]
    creator_id: int
    created_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True
