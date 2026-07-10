"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, comments, tickets, workspaces
# from .notifications import start_worker, stop_worker  # PROPOSED FIX: queue-based notifications
# from fastapi.exceptions import RequestValidationError  # PROPOSED FIX: consistent error model
# from fastapi.responses import JSONResponse  # PROPOSED FIX: consistent error model
# from starlette.exceptions import HTTPException as StarletteHTTPException  # PROPOSED FIX: consistent error model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ticket Tracker API")

# PROPOSED FIX: start the background delivery thread (and its startup
# pending-notification sweep) once per worker process, and stop it
# cleanly on shutdown. Using on_event here rather than a lifespan
# contextmanager to keep this a minimal, isolated diff against the
# existing app construction above -- worth revisiting if this file grows
# more startup/shutdown concerns later.
#
# @app.on_event("startup")
# def _on_startup():
#     start_worker()
#
#
# @app.on_event("shutdown")
# def _on_shutdown():
#     stop_worker()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tickets.router)
app.include_router(comments.router)

# PROPOSED FIX: no consistent error model. `raise HTTPException(detail="...")`
# call sites return a bare string in `detail`, while FastAPI's own
# request-validation failures (422s -- bad enum value, missing required
# field, wrong type) return a totally different shape:
# `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`. A client
# has to special-case parsing depending on which kind of error it got.
# These two handlers normalize both into the same
# `{"error": {"code": ..., "message": ...}}` envelope -- and since they
# wrap *any* HTTPException, every existing call site is covered without
# needing to touch each one individually (see errors.py for the optional
# `api_error()` helper for call sites that want a specific, stable code
# instead of the generic "http_error" fallback below).
#
# @app.exception_handler(StarletteHTTPException)
# async def _http_exception_handler(request, exc):
#     detail = exc.detail
#     body = (
#         detail
#         if isinstance(detail, dict) and "error" in detail
#         else {"error": {"code": "http_error", "message": str(detail)}}
#     )
#     return JSONResponse(status_code=exc.status_code, content=body)
#
#
# @app.exception_handler(RequestValidationError)
# async def _validation_exception_handler(request, exc):
#     return JSONResponse(
#         status_code=422,
#         content={
#             "error": {
#                 "code": "validation_error",
#                 "message": "Invalid request",
#                 "fields": exc.errors(),
#             }
#         },
#     )


@app.get("/health")
def health():
    return {"status": "ok"}
