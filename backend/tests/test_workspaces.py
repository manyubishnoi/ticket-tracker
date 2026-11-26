def test_create_workspace(client, alice_headers):
    resp = client.post("/workspaces", json={"name": "Engineering", "key": "ENG"}, headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Engineering"
    assert body["key"] == "ENG"


def test_list_workspaces_only_shows_members(client, alice_headers, bob_headers):
    client.post("/workspaces", json={"name": "Engineering", "key": "ENG"}, headers=alice_headers)
    # Bob is not a member of Alice's workspace.
    resp = client.get("/workspaces", headers=bob_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_creator_sees_own_workspace(client, alice_headers, workspace):
    resp = client.get("/workspaces", headers=alice_headers)
    names = [w["name"] for w in resp.json()]
    assert "Engineering" in names


def test_list_members_returns_all_members(client, alice_headers, workspace, bob_in_workspace):
    resp = client.get(f"/workspaces/{workspace['id']}/members", headers=alice_headers)
    assert resp.status_code == 200
    members = {m["email"]: m for m in resp.json()}
    assert members["alice@example.com"]["name"] == "Alice"
    assert members["alice@example.com"]["role"] == "admin"
    assert members["bob@example.com"]["name"] == "Bob"
    assert members["bob@example.com"]["role"] == "member"


def test_list_members_requires_membership(client, workspace, carol_headers):
    resp = client.get(f"/workspaces/{workspace['id']}/members", headers=carol_headers)
    assert resp.status_code == 403


def test_list_members_excludes_password_hash(client, alice_headers, workspace):
    resp = client.get(f"/workspaces/{workspace['id']}/members", headers=alice_headers)
    assert resp.status_code == 200
    for member in resp.json():
        assert "password_hash" not in member
