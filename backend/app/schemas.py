"""Pydantic schemas."""
from datetime import datetime
from typing import Optional
# from enum import Enum  # PROPOSED FIX: needed for TicketStatus/TicketPriority below

from pydantic import BaseModel, EmailStr

# PROPOSED FIX: status/priority are free strings today (models.py just
# documents the intended values in a comment: "open|in_progress|done|
# canceled" and "none|low|medium|high|urgent"), so nothing stops a caller
# from writing e.g. status="oepn" -- a typo silently creates a new,
# permanent, invalid status that every "is it open/done" check in the app
# (workspace_stats, any future filter) will silently miscount instead of
# rejecting. `str, Enum` mixins validate against the exact set below,
# serialize as plain strings (no wire-format change), and show up as a
# dropdown of allowed values in the OpenAPI docs.
#
# class TicketStatus(str, Enum):
#     open = "open"
#     in_progress = "in_progress"
#     done = "done"
#     canceled = "canceled"
#
#
# class TicketPriority(str, Enum):
#     none = "none"
#     low = "low"
#     medium = "medium"
#     high = "high"
#     urgent = "urgent"


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

# PROPOSED FIX: same mass-assignment pattern as the original TicketUpdate,
# but worse here -- auth.py's update_me() does the identical
# `setattr(current_user, field, value)` loop over this payload, so any
# authenticated user can PATCH /me with {"is_admin": true} and grant
# themselves admin, or overwrite their own password_hash directly
# (bypassing hash_password entirely), or their id/created_at. Explicit
# whitelist + extra="forbid" closes this the same way as TicketUpdate.
#
# class UserUpdate(BaseModel):
#     name: Optional[str] = None
#     email: Optional[EmailStr] = None
#
#     class Config:
#         extra = "forbid"


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
    # priority: TicketPriority = TicketPriority.none  # PROPOSED FIX
    assignee_id: Optional[int] = None


class TicketUpdate(BaseModel):
    # Partial update; any provided field is applied to the ticket.
    class Config:
        extra = "allow"

# PROPOSED FIX: was mass-assignment — extra="allow" with no fields defined
# meant callers could PATCH arbitrary columns (workspace_id, creator_id,
# is_deleted, id, ...) via tickets.py's `setattr(ticket, field, value)`
# loop. Explicit optional fields + extra="forbid" makes pydantic reject
# anything not in this whitelist before it ever reaches the router. status
# and priority are additionally typed as the enums above instead of bare
# str, so e.g. status="oepn" is rejected at validation time instead of
# silently becoming a permanent, un-matched status value on the ticket.
#
# class TicketUpdate(BaseModel):
#     title: Optional[str] = None
#     description: Optional[str] = None
#     status: Optional[TicketStatus] = None
#     priority: Optional[TicketPriority] = None
#     assignee_id: Optional[int] = None
#
#     class Config:
#         extra = "forbid"


class TicketOut(BaseModel):
    id: int
    workspace_id: int
    identifier: str
    title: str
    description: str
    status: str
    # status: TicketStatus  # PROPOSED FIX
    priority: str
    # priority: TicketPriority  # PROPOSED FIX -- note: any row already in the DB
    # with a value outside these enums (e.g. from the current free-string
    # column, or from before this fix was activated) would fail to serialize
    # once this is turned on. Worth a quick `SELECT DISTINCT status, priority
    # FROM tickets` check against the enum values before activating.
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


# PROPOSED FIX: no consistent error model. Right now every raise looks like
# `HTTPException(status_code=404, detail="Ticket not found")` -- a bare
# string -- while FastAPI's own request-validation failures (422s) come
# back shaped completely differently: `{"detail": [{"loc": ..., "msg": ...,
# "type": ...}]}`. A client has to special-case parsing per error source.
# These two schemas (used by the global exception handlers proposed in
# main.py, see errors.py) give every error response -- explicit or
# validation -- the same envelope: `{"error": {"code": ..., "message": ...}}`.
#
# class ErrorDetail(BaseModel):
#     code: str
#     message: str
#
#
# class ErrorResponse(BaseModel):
#     error: ErrorDetail
