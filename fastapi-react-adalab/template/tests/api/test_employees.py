from datetime import date

from fastapi.testclient import TestClient

from app.models.department import Department


def _payload(department: Department, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "first_name": "Alice",
        "last_name": "Ng",
        "email": "alice@example.com",
        "title": "Engineer",
        "department_id": department.id,
        "hire_date": date(2024, 1, 15).isoformat(),
        "is_active": True,
    }
    base.update(overrides)
    return base


def test_list_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.get("/api/employees", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get(
    client: TestClient, auth_headers: dict[str, str], department: Department
) -> None:
    r = client.post("/api/employees", json=_payload(department), headers=auth_headers)
    assert r.status_code == 201
    created = r.json()
    assert created["first_name"] == "Alice"
    assert created["email"] == "alice@example.com"
    assert "id" in created

    emp_id = created["id"]
    r = client.get(f"/api/employees/{emp_id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == emp_id
    assert body["title"] == "Engineer"


def test_create_duplicate_fails(
    client: TestClient, auth_headers: dict[str, str], department: Department
) -> None:
    payload = _payload(department)
    r = client.post("/api/employees", json=payload, headers=auth_headers)
    assert r.status_code == 201

    r = client.post("/api/employees", json=payload, headers=auth_headers)
    assert r.status_code == 409


def test_update(client: TestClient, auth_headers: dict[str, str], department: Department) -> None:
    r = client.post("/api/employees", json=_payload(department), headers=auth_headers)
    emp_id = r.json()["id"]

    r = client.patch(
        f"/api/employees/{emp_id}",
        json={"title": "Senior Engineer"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Senior Engineer"
    assert body["first_name"] == "Alice"


def test_delete(client: TestClient, auth_headers: dict[str, str], department: Department) -> None:
    r = client.post("/api/employees", json=_payload(department), headers=auth_headers)
    emp_id = r.json()["id"]

    r = client.delete(f"/api/employees/{emp_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/employees/{emp_id}", headers=auth_headers)
    assert r.status_code == 404


def test_unauthenticated_returns_401(client: TestClient) -> None:
    r = client.get("/api/employees")
    assert r.status_code == 401


def test_invalid_email_returns_422(
    client: TestClient, auth_headers: dict[str, str], department: Department
) -> None:
    r = client.post(
        "/api/employees",
        json=_payload(department, email="not-an-email"),
        headers=auth_headers,
    )
    assert r.status_code == 422
