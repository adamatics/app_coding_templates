from fastapi.testclient import TestClient


def test_list_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.get("/api/departments", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/departments",
        json={"name": "Engineering", "code": "ENG", "description": "Builds stuff"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Engineering"
    assert created["code"] == "ENG"
    assert "id" in created

    dep_id = created["id"]
    r = client.get(f"/api/departments/{dep_id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == dep_id
    assert body["description"] == "Builds stuff"


def test_create_duplicate_fails(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {"name": "HR", "code": "HR"}
    r = client.post("/api/departments", json=payload, headers=auth_headers)
    assert r.status_code == 201

    r = client.post("/api/departments", json=payload, headers=auth_headers)
    assert r.status_code == 409


def test_update(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/departments",
        json={"name": "Finance", "code": "FIN"},
        headers=auth_headers,
    )
    dep_id = r.json()["id"]

    r = client.patch(
        f"/api/departments/{dep_id}",
        json={"description": "updated"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["description"] == "updated"
    assert body["name"] == "Finance"


def test_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/departments",
        json={"name": "Legal", "code": "LEG"},
        headers=auth_headers,
    )
    dep_id = r.json()["id"]

    r = client.delete(f"/api/departments/{dep_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/departments/{dep_id}", headers=auth_headers)
    assert r.status_code == 404


def test_unauthenticated_returns_401(client: TestClient) -> None:
    r = client.get("/api/departments")
    assert r.status_code == 401


def test_invalid_code_format_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/departments",
        json={"name": "Bad", "code": "lowercase"},
        headers=auth_headers,
    )
    assert r.status_code == 422
