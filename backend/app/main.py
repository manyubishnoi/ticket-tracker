"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, comments, tickets, workspaces

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ticket Tracker API")

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


@app.get("/health")
def health():
    return {"status": "ok"}
