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
