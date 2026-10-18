from app.extensions import db
from app.models import AuditEvent, User


def test_admin_dashboard_access(client, auth):
    auth.login("admin_user", "AdminPass123!")
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Administration Center" in response.data
    assert b"User Accounts & Role Permissions" in response.data


def test_admin_toggle_user_active(client, auth, app):
    auth.login("admin_user", "AdminPass123!")

    with app.app_context():
        emp = User.query.filter_by(username="emp_bob").first()
        emp_id = emp.id
        assert emp.active is True

    # Deactivate Bob
    response = client.post(f"/admin/users/{emp_id}/toggle-active", follow_redirects=True)
    assert response.status_code == 200
    assert b"deactivated" in response.data

    with app.app_context():
        assert db.session.get(User, emp_id).active is False

    # Reactivate Bob
    response = client.post(f"/admin/users/{emp_id}/toggle-active", follow_redirects=True)
    assert response.status_code == 200
    assert b"activated" in response.data

    with app.app_context():
        assert db.session.get(User, emp_id).active is True


def test_admin_cannot_deactivate_self(client, auth, app):
    auth.login("admin_user", "AdminPass123!")

    with app.app_context():
        admin = User.query.filter_by(username="admin_user").first()
        admin_id = admin.id

    response = client.post(f"/admin/users/{admin_id}/toggle-active", follow_redirects=True)
    assert response.status_code == 200
    assert b"cannot deactivate your own" in response.data

    with app.app_context():
        assert db.session.get(User, admin_id).active is True


def test_admin_change_user_role(client, auth, app):
    auth.login("admin_user", "AdminPass123!")

    with app.app_context():
        emp = User.query.filter_by(username="emp_bob").first()
        emp_id = emp.id

    response = client.post(
        f"/admin/users/{emp_id}/change-role",
        data={"role": "reviewer"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"changed from employee to reviewer" in response.data

    with app.app_context():
        assert db.session.get(User, emp_id).role == "reviewer"


def test_admin_challenge_mode_flag(client, auth, app):
    app.config["CHALLENGE_MODE"] = True
    app.config["CHALLENGE_FLAG"] = "FLAG{test_challenge_flag_12345}"

    auth.login("admin_user", "AdminPass123!")
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"FLAG{test_challenge_flag_12345}" in response.data
    assert b"CHALLENGE ACTIVE" in response.data
