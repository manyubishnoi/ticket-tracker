import pytest


@pytest.fixture()
def ticket(client, alice_headers, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/tickets",
        json={"title": "Commentable", "priority": "low"},
        headers=alice_headers,
    )
    return resp.json()


def test_create_comment(client, alice_headers, ticket):
    resp = client.post(
        f"/tickets/{ticket['id']}/comments",
        json={"body": "Looking into this"},
        headers=alice_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["body"] == "Looking into this"


def test_list_comments(client, alice_headers, ticket):
    client.post(f"/tickets/{ticket['id']}/comments", json={"body": "one"}, headers=alice_headers)
    client.post(f"/tickets/{ticket['id']}/comments", json={"body": "two"}, headers=alice_headers)
    resp = client.get(f"/tickets/{ticket['id']}/comments", headers=alice_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
