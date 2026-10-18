from app.extensions import db
from app.models import Document, User


def test_dashboard_unauthenticated_redirects(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_employee_dashboard(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Alice Private Draft",
            content="Confidential content",
            category="Engineering",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()

    auth.login("emp_alice", "EmployeePass123!")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Employee Document Workspace" in response.data
    assert b"Alice Private Draft" in response.data


def test_reviewer_dashboard(client, auth):
    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Reviewer Dashboard" in response.data
    assert b"Review Queue" in response.data


def test_admin_dashboard_stats(client, auth):
    auth.login("admin_user", "AdminPass123!")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"System Administrator Overview" in response.data
    assert b"Active Users" in response.data
