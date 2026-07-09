"""Populate the database with demo data.

Run with:  python -m app.seed
"""
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import Comment, Membership, Ticket, User, Workspace


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Data already present; skipping seed.")
            return

        alice = User(email="alice@example.com", name="Alice", password_hash=hash_password("password123"), is_admin=True)
        bob = User(email="bob@example.com", name="Bob", password_hash=hash_password("password123"))
        carol = User(email="carol@example.com", name="Carol", password_hash=hash_password("password123"))
        db.add_all([alice, bob, carol])
        db.commit()

        eng = Workspace(name="Engineering", key="ENG", owner_id=alice.id)
        design = Workspace(name="Design", key="DES", owner_id=carol.id)
        db.add_all([eng, design])
        db.commit()

        db.add_all([
            Membership(user_id=alice.id, workspace_id=eng.id, role="admin"),
            Membership(user_id=bob.id, workspace_id=eng.id, role="member"),
            Membership(user_id=carol.id, workspace_id=design.id, role="admin"),
        ])
        db.commit()

        t1 = Ticket(workspace_id=eng.id, identifier="ENG-1", title="Login page 500s on empty password",
                    description="Repro: submit login with blank password.", status="open", priority="high",
                    assignee_id=bob.id, creator_id=alice.id)
        t2 = Ticket(workspace_id=eng.id, identifier="ENG-2", title="Add dark mode",
                    description="Design wants a dark theme.", status="in_progress", priority="medium",
                    assignee_id=bob.id, creator_id=alice.id)
        t3 = Ticket(workspace_id=design.id, identifier="DES-1", title="New icon set",
                    description="Refresh the sidebar icons.", status="open", priority="low",
                    creator_id=carol.id)
        db.add_all([t1, t2, t3])
        db.commit()

        db.add_all([
            Comment(ticket_id=t1.id, author_id=bob.id, body="I can reproduce this."),
            Comment(ticket_id=t1.id, author_id=alice.id, body="Thanks, prioritizing."),
        ])
        db.commit()
        print("Seeded demo data.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
