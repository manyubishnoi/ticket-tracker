"""Notification helpers."""
import time

# In-memory outbox. Works fine in a single process.
_OUTBOX = []


def send_notification(user_id: int, message: str) -> None:
    # Simulate talking to an external notification provider.
    time.sleep(0.05)
    _OUTBOX.append({"user_id": user_id, "message": message})


def outbox_size() -> int:
    return len(_OUTBOX)


# PROPOSED FIX: queue-based, DB-backed replacement for the two problems
# called out earlier:
#   1. `_OUTBOX` is per-process memory -- broken/inconsistent under
#      multiple workers, and lost on restart or crash.
#   2. `send_notification()` blocks with `time.sleep(0.05)` on whatever
#      thread calls it directly, which is disastrous if called from an
#      `async def` route (blocks the whole worker's event loop).
#
# Design: the request path only ever does a fast, synchronous DB insert
# (a `Notification` row, status="pending") and hands the id to a
# `queue.Queue` -- a plain thread-safe stdlib queue, not asyncio.Queue,
# specifically so it can be fed safely from Starlette's sync-handler
# threadpool without any event-loop bridging. A single dedicated background
# *thread* per worker process drains that queue, does the (still
# artificially slow) "call the provider" step off of any request-serving
# thread or the event loop, and flips the row to sent/failed. Because the
# durable state lives in the `notifications` table (shared DB, not
# in-process memory), a startup sweep can re-queue anything left "pending"
# from a prior crash -- in any worker, not just the one that inserted it.
#
# import queue
# import threading
# from datetime import datetime
#
# from .database import SessionLocal
# from .models import Notification
#
# _QUEUE: "queue.Queue[int]" = queue.Queue()
# _STOP = object()
# _worker_thread: "threading.Thread | None" = None
#
#
# def enqueue_notification(db, user_id: int, message: str) -> Notification:
#     """Persist a notification and schedule it for async delivery.
#
#     Takes the caller's existing `db` session so the row is created in the
#     same request/transaction as the ticket it's attached to, then hands
#     off only the id -- the background thread uses its own session.
#     """
#     notification = Notification(user_id=user_id, message=message, status="pending")
#     db.add(notification)
#     db.commit()
#     db.refresh(notification)
#     _QUEUE.put(notification.id)
#     return notification
#
#
# def _deliver(notification_id: int) -> None:
#     db = SessionLocal()
#     try:
#         notification = db.query(Notification).filter(Notification.id == notification_id).first()
#         if notification is None or notification.status != "pending":
#             return
#         try:
#             time.sleep(0.05)  # Simulate talking to an external notification provider.
#         except Exception:
#             notification.status = "failed"
#         else:
#             notification.status = "sent"
#             notification.sent_at = datetime.utcnow()
#         db.add(notification)
#         db.commit()
#     finally:
#         db.close()
#
#
# def _worker_loop() -> None:
#     while True:
#         item = _QUEUE.get()
#         if item is _STOP:
#             return
#         try:
#             _deliver(item)
#         except Exception:
#             # One bad notification should not kill the worker thread.
#             pass
#
#
# def _requeue_pending() -> None:
#     """On startup, pick back up anything left mid-flight by a crash."""
#     db = SessionLocal()
#     try:
#         stuck = db.query(Notification).filter(Notification.status == "pending").all()
#         for notification in stuck:
#             _QUEUE.put(notification.id)
#     finally:
#         db.close()
#
#
# def start_worker() -> None:
#     """Call once from the app's startup hook (see main.py)."""
#     global _worker_thread
#     if _worker_thread is not None:
#         return
#     _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
#     _worker_thread.start()
#     _requeue_pending()
#
#
# def stop_worker() -> None:
#     """Call once from the app's shutdown hook (see main.py)."""
#     _QUEUE.put(_STOP)
