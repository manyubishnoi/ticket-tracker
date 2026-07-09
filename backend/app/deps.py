"""Request dependencies."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import get_db
from .models import User


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    # Reflect admin status from the token so we don't hit the DB again.
    user.is_admin = payload.get("is_admin", False)
    return user
