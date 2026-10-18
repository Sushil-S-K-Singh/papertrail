def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["version"] == "1.0.0"


def test_custom_404_error_page(client):
    response = client.get("/nonexistent-page-that-does-not-exist")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"Resource Not Found" in response.data


def test_custom_403_error_page(client, auth):
    auth.login("emp_alice", "EmployeePass123!")
    response = client.get("/admin")
    assert response.status_code == 403
    assert b"403" in response.data
    assert b"Access Restricted" in response.data


def test_audit_log_page(client, auth):
    auth.login("emp_alice", "EmployeePass123!")
    response = client.get("/audit")
    assert response.status_code == 200
    assert b"Enterprise Audit Trail" in response.data


def test_audit_log_filter(client, auth):
    auth.login("admin_user", "AdminPass123!")
    response = client.get("/audit?event_type=auth.login_success")
    assert response.status_code == 200
    assert b"auth.login_success" in response.data
