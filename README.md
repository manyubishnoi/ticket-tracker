# Ticket Tracker

A lightweight, Linear-style issue tracker. Users belong to workspaces, create
tickets with an auto-generated identifier (e.g. `ENG-14`), comment on them, and
track status and priority.

- **Backend:** FastAPI + SQLAlchemy (SQLite by default)
- **Frontend:** Next.js (App Router, TypeScript)

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Seed some demo data (optional)
python -m app.seed

# Run the API
uvicorn app.main:app --reload
```

The API is then available at http://localhost:8000 (interactive docs at `/docs`).

### Tests

```bash
cd backend
pytest
```

### Demo accounts (after seeding)

| Email               | Password       | Notes           |
| ------------------- | -------------- | --------------- |
| alice@example.com   | password123    | Engineering (admin) |
| bob@example.com     | password123    | Engineering     |
| carol@example.com   | password123    | Design (admin)  |

## Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Then open http://localhost:3000.

## Domain model

- **User** — an account that can belong to one or more workspaces.
- **Workspace** — a container for tickets; has a short `key` (e.g. `ENG`).
- **Membership** — links a user to a workspace with a role.
- **Ticket** — an issue with status, priority, assignee, and comments.
- **Comment** — a message on a ticket.
- **Activity** — an audit entry recording ticket events.

## API overview

| Method | Path                                   | Description                 |
| ------ | -------------------------------------- | --------------------------- |
| POST   | `/signup`, `/login`                    | Auth                        |
| GET    | `/me`, PATCH `/me`                      | Current user                |
| POST   | `/workspaces`                          | Create workspace            |
| GET    | `/workspaces`                          | List your workspaces        |
| DELETE | `/workspaces/{id}`                     | Delete a workspace          |
| POST   | `/workspaces/{id}/tickets`             | Create a ticket             |
| POST   | `/workspaces/{id}/tickets/bulk`        | Bulk-create tickets         |
| GET    | `/workspaces/{id}/tickets`             | List tickets (paginated)    |
| GET    | `/workspaces/{id}/stats`               | Workspace stats             |
| GET    | `/tickets/search?q=`                   | Search tickets              |
| GET    | `/tickets/{id}`                        | Get a ticket                |
| PATCH  | `/tickets/{id}`                        | Update a ticket             |
| DELETE | `/tickets/{id}`                        | Delete a ticket             |
| POST   | `/tickets/{id}/comments`               | Add a comment               |
| GET    | `/tickets/{id}/comments`               | List comments               |
