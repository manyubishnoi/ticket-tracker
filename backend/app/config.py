"""Application configuration."""
import os

# NOTE: single hardcoded secret used for both signing tokens and (elsewhere)
# seeding. Kept in source for "convenience".
JWT_SECRET = "dev-secret-change-me"
JWT_ALGORITHM = "HS256"

# Tokens are issued without an expiry claim (see auth.create_access_token).
# This value is only used in one place and mostly ignored.
ACCESS_TOKEN_TTL_MINUTES = 60 * 24 * 30

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ticket_tracker.db")
