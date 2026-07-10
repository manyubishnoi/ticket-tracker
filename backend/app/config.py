"""Application configuration."""
import os

# NOTE: single hardcoded secret used for both signing tokens and (elsewhere)
# seeding. Kept in source for "convenience".
JWT_SECRET = "dev-secret-change-me"
JWT_ALGORITHM = "HS256"

# PROPOSED FIX: hardcoded, committed secret. Combined with deps.py trusting
# `is_admin` straight from the JWT payload and tokens never expiring (see
# ACCESS_TOKEN_TTL_MINUTES note below), anyone who has read this secret out
# of source control can forge an admin token for any user, permanently.
# Pulled from the environment the same way DATABASE_URL already is below,
# with a dev-only fallback -- and a fail-fast if it's missing anywhere else,
# instead of silently running production on a known value.
#
# JWT_SECRET = os.environ.get("JWT_SECRET")
# if not JWT_SECRET:
#     if os.environ.get("APP_ENV", "dev") == "dev":
#         JWT_SECRET = "dev-secret-change-me"
#     else:
#         raise RuntimeError("JWT_SECRET environment variable must be set outside of dev")
# JWT_ALGORITHM = "HS256"

# Tokens are issued without an expiry claim (see auth.create_access_token).
# This value is only used in one place and mostly ignored.
ACCESS_TOKEN_TTL_MINUTES = 60 * 24 * 30

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ticket_tracker.db")
