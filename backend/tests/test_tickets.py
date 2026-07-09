import pytest


@pytest.fixture()
def ticket(client, alice_headers, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "First bug", "description": "something broke", "priority": "high"},
        headers=alice_headers,
    )
    return resp.json()


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
