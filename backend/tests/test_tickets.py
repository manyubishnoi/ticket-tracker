from datetime import datetime, timedelta

import pytest

from app.models import Ticket


@pytest.fixture()
def ticket(client, alice_headers, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "First bug", "description": "something broke", "priority": "high"},
        headers=alice_headers,
    )
    return resp.json()


def _set_timestamps(db_session, ticket_id, created_at=None, updated_at=None):
    t = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if created_at is not None:
        t.created_at = created_at
    if updated_at is not None:
        t.updated_at = updated_at
    db_session.add(t)
    db_session.commit()


def test_create_ticket_assigns_identifier(client, alice_headers, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "A bug", "priority": "medium"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "ENG-1"


def test_identifiers_increment(client, alice_headers, workspace):
    for i in range(3):
        client.post(
            f"/workspaces/{workspace['id']}/tickets",
            json={"title": f"Bug {i}"},
            headers=alice_headers,
        )
    resp = client.get(f"/workspaces/{workspace['id']}/tickets", headers=alice_headers)
    ids = [t["identifier"] for t in resp.json()]
    assert ids == ["ENG-1", "ENG-2", "ENG-3"]


def test_get_ticket(client, alice_headers, ticket):
    resp = client.get(f"/tickets/{ticket['id']}", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "First bug"


def test_update_ticket_status(client, alice_headers, ticket):
    resp = client.patch(
        f"/tickets/{ticket['id']}",
        json={"status": "done"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["closed_at"] is not None


def test_soft_delete_hides_from_list(client, alice_headers, workspace, ticket):
    client.delete(f"/tickets/{ticket['id']}", headers=alice_headers)
    resp = client.get(f"/workspaces/{workspace['id']}/tickets", headers=alice_headers)
    ids = [t["id"] for t in resp.json()]
    assert ticket["id"] not in ids


def test_search_returns_matching_ticket(client, alice_headers, ticket):
    resp = client.get("/tickets/search", params={"q": "First"}, headers=alice_headers)
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "First bug" in titles


def test_stats_counts_tickets(client, alice_headers, workspace, ticket):
    resp = client.get(f"/workspaces/{workspace['id']}/stats", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.json()["total_tickets"] >= 1


def test_ticket_out_includes_updated_at(client, alice_headers, ticket):
    assert ticket["updated_at"] is not None
    created = datetime.fromisoformat(ticket["created_at"])
    updated = datetime.fromisoformat(ticket["updated_at"])
    assert abs((updated - created).total_seconds()) < 1


def test_update_ticket_bumps_updated_at(client, alice_headers, ticket):
    original_updated_at = ticket["updated_at"]
    resp = client.patch(
        f"/tickets/{ticket['id']}",
        json={"title": "Renamed bug"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated_at"] >= original_updated_at


def test_list_tickets_filters_by_assignee_id(client, alice_headers, workspace, bob_in_workspace):
    client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "Assigned to bob", "assignee_id": bob_in_workspace.id},
        headers=alice_headers,
    )
    client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "Unassigned"},
        headers=alice_headers,
    )
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"assignee_id": bob_in_workspace.id},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Assigned to bob"]


def test_list_tickets_assignee_id_nonexistent_returns_empty(client, alice_headers, workspace, ticket):
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"assignee_id": 999999},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tickets_assignee_id_non_integer_422(client, alice_headers, workspace):
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"assignee_id": "notanumber"},
        headers=alice_headers,
    )
    assert resp.status_code == 422


def test_list_tickets_filters_by_priority(client, alice_headers, workspace):
    client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "Low prio", "priority": "low"},
        headers=alice_headers,
    )
    client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "Urgent prio", "priority": "urgent"},
        headers=alice_headers,
    )
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"priority": "urgent"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Urgent prio"]


def test_list_tickets_invalid_priority_422(client, alice_headers, workspace):
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"priority": "invalid_value"},
        headers=alice_headers,
    )
    assert resp.status_code == 422


def test_list_tickets_sort_by_created_at_desc(client, alice_headers, workspace, db_session):
    ids = []
    for i in range(3):
        resp = client.post(
            f"/workspaces/{workspace['id']}/tickets",
            json={"title": f"Bug {i}"},
            headers=alice_headers,
        )
        ids.append(resp.json()["id"])

    base = datetime(2024, 1, 1)
    for i, ticket_id in enumerate(ids):
        _set_timestamps(db_session, ticket_id, created_at=base + timedelta(days=i))

    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"sort_by": "created_at", "order": "desc"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == list(reversed(ids))


def test_list_tickets_sort_by_updated_at_asc(client, alice_headers, workspace, db_session):
    ids = []
    for i in range(3):
        resp = client.post(
            f"/workspaces/{workspace['id']}/tickets",
            json={"title": f"Bug {i}"},
            headers=alice_headers,
        )
        ids.append(resp.json()["id"])

    # Set updated_at in the reverse order of creation, and created_at all
    # equal, to prove the sort is actually on updated_at and not created_at.
    base = datetime(2024, 1, 1)
    same_created_at = datetime(2024, 6, 1)
    for i, ticket_id in enumerate(ids):
        _set_timestamps(
            db_session,
            ticket_id,
            created_at=same_created_at,
            updated_at=base + timedelta(days=(len(ids) - i)),
        )

    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"sort_by": "updated_at", "order": "asc"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == list(reversed(ids))


def test_list_tickets_invalid_sort_by_422(client, alice_headers, workspace):
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"sort_by": "titles"},
        headers=alice_headers,
    )
    assert resp.status_code == 422


def test_list_tickets_invalid_order_422(client, alice_headers, workspace):
    resp = client.get(
        f"/workspaces/{workspace['id']}/tickets",
        params={"order": "sideways"},
        headers=alice_headers,
    )
    assert resp.status_code == 422


def test_list_tickets_default_sort_unchanged(client, alice_headers, workspace):
    for i in range(3):
        client.post(
            f"/workspaces/{workspace['id']}/tickets",
            json={"title": f"Bug {i}"},
            headers=alice_headers,
        )
    resp = client.get(f"/workspaces/{workspace['id']}/tickets", headers=alice_headers)
    ids = [t["identifier"] for t in resp.json()]
    assert ids == ["ENG-1", "ENG-2", "ENG-3"]
