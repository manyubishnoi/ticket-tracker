"""ORM models."""
from datetime import datetime
# from datetime import timezone  # PROPOSED FIX: needed for the tz-aware-then-stripped helper below

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    # UniqueConstraint,  # PROPOSED FIX: needed for the Ticket backstop constraint below
)
from sqlalchemy.orm import relationship

from .database import Base

# PROPOSED FIX: datetime.utcnow() is deprecated (Python 3.12+) and naive.
# This computes the same naive-UTC value via the non-deprecated aware API,
# then strips tzinfo so it round-trips identically through SQLite's plain
# DateTime columns (which have no offset storage) and stays comparable to
# every other naive datetime already in the DB. All 5 `default=datetime.utcnow`
# columns below get their default swapped to this helper.
#
# def _utcnow_naive() -> datetime:
#     return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=_utcnow_naive, nullable=False)  # PROPOSED FIX


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    key = Column(String, nullable=False)  # e.g. "ENG", used for ticket identifiers
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=_utcnow_naive, nullable=False)  # PROPOSED FIX
    # ticket_sequence = Column(Integer, default=0, nullable=False)
    # PROPOSED FIX: persistent per-workspace counter, atomically incremented
    # via `UPDATE ... SET ticket_sequence = ticket_sequence + 1 RETURNING ...`
    # in tickets.py. Replaces counting non-deleted tickets, which broke once
    # a ticket was soft-deleted (count shrinks, next number reuses one
    # that's still active) and raced under concurrent creates.

    memberships = relationship("Membership", back_populates="workspace")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    role = Column(String, default="member", nullable=False)  # member | admin

    workspace = relationship("Workspace", back_populates="memberships")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    identifier = Column(String, nullable=False)  # e.g. "ENG-14"
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="open", nullable=False)  # open|in_progress|done|canceled
    priority = Column(String, default="none", nullable=False)  # none|low|medium|high|urgent
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=_utcnow_naive, nullable=False)  # PROPOSED FIX
    closed_at = Column(DateTime, nullable=True)

    # __table_args__ = (
    #     UniqueConstraint("workspace_id", "identifier", name="uq_ticket_workspace_identifier"),
    # )
    # PROPOSED FIX: DB-level backstop. Even with the sequence-based
    # generator fixed in tickets.py, nothing today stops a duplicate
    # identifier from being written (no constraint exists at all). This
    # makes a collision raise an IntegrityError instead of silently
    # succeeding, whatever the cause.

    comments = relationship("Comment", back_populates="ticket")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=_utcnow_naive, nullable=False)  # PROPOSED FIX

    ticket = relationship("Ticket", back_populates="comments")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)  # created|status_changed|assigned|commented
    detail = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=_utcnow_naive, nullable=False)  # PROPOSED FIX


# PROPOSED FIX: durable, DB-backed notifications. Replaces the in-memory
# `_OUTBOX` list in notifications.py, which is per-process (broken across
# multiple workers) and lost on restart/crash. Persisting a row per
# notification also gives you the analytics record requested — query by
# user, status, or created_at without touching any in-memory state.
#
# class Notification(Base):
#     __tablename__ = "notifications"
#
#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     message = Column(String, nullable=False)
#     status = Column(String, default="pending", nullable=False)  # pending|sent|failed
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     sent_at = Column(DateTime, nullable=True)
