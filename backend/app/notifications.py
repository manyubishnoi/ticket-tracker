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
