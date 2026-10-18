from app.models import AuditEvent, User


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"PaperTrail" in response.data
    assert b"Transparent, Secure Document Approvals" in response.data


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign In to PaperTrail" in response.data


def test_login_success(client, auth):
    response = auth.login("emp_alice", "EmployeePass123!")
    assert response.status_code == 200
    assert b"Welcome back, emp_alice!" in response.data
    assert b"Sign Out" in response.data


def test_login_failure_wrong_password(client, auth):
    response = auth.login("emp_alice", "WrongPassword!")
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_failure_nonexistent_user(client, auth):
    response = auth.login("nonexistent_user", "AnyPassword123!")
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_deactivated_account(client, auth):
    response = auth.login("disabled_user", "EmployeePass123!")
    assert response.status_code == 200
    assert b"deactivated" in response.data


def test_logout(client, auth):
    auth.login("emp_alice", "EmployeePass123!")
    response = auth.logout()
    assert response.status_code == 200
    assert b"You have been signed out successfully" in response.data


def test_dev_register_employee(client, app):
    response = client.post(
        "/dev-register",
        data={
            "username": "new_tester",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "employee",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Test account created successfully" in response.data

    with app.app_context():
        user = User.query.filter_by(username="new_tester").first()
        assert user is not None
        assert user.role == "employee"
        assert user.check_password("Password123!")
        assert not user.password_hash.startswith("Password123!")


def test_dev_register_rejects_admin_role(client):
    response = client.post(
        "/dev-register",
        data={
            "username": "fake_admin",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Only employee or reviewer accounts may be registered" in response.data


def test_dev_register_mismatched_password(client):
    response = client.post(
        "/dev-register",
        data={
            "username": "mismatch_user",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
            "role": "employee",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_audit_event_logged_on_login(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")
    with app.app_context():
        user = User.query.filter_by(username="emp_alice").first()
        audit = AuditEvent.query.filter_by(event_type="auth.login_success", actor_id=user.id).first()
        assert audit is not None
