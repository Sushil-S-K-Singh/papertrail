from app.extensions import db
from app.models import Document, User


def test_employee_cannot_view_another_employees_draft(client, auth, app):
    with app.app_context():
        bob = User.query.filter_by(username="emp_bob").first()
        doc = Document(
            owner_id=bob.id,
            title="Bob Secret Plan",
            content="Top secret content",
            category="Legal",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    # Alice attempts to view Bob's draft
    auth.login("emp_alice", "EmployeePass123!")
    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 403
    assert b"Access Restricted" in response.data


def test_employee_cannot_edit_another_employees_document(client, auth, app):
    with app.app_context():
        bob = User.query.filter_by(username="emp_bob").first()
        doc = Document(
            owner_id=bob.id,
            title="Bob Document",
            content="Bob content",
            category="Legal",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")
    response = client.post(
        f"/documents/{doc_id}/edit",
        data={"title": "Hacked Title", "content": "Tampered content", "action": "save_draft"},
    )
    assert response.status_code == 403


def test_employee_cannot_delete_another_employees_document(client, auth, app):
    with app.app_context():
        bob = User.query.filter_by(username="emp_bob").first()
        doc = Document(
            owner_id=bob.id,
            title="Bob Document to keep",
            content="Content",
            category="Legal",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")
    response = client.post(f"/documents/{doc_id}/delete")
    assert response.status_code == 403

    with app.app_context():
        assert db.session.get(Document, doc_id) is not None


def test_employee_cannot_access_admin_dashboard(client, auth):
    auth.login("emp_alice", "EmployeePass123!")
    response = client.get("/admin")
    assert response.status_code == 403


def test_reviewer_cannot_access_admin_dashboard(client, auth):
    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.get("/admin")
    assert response.status_code == 403


def test_employee_cannot_access_review_queue(client, auth):
    auth.login("emp_alice", "EmployeePass123!")
    response = client.get("/reviews")
    assert response.status_code == 403


def test_cannot_delete_approved_document(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Approved Compliance Doc",
            content="Content",
            category="Legal",
            status="approved",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")
    response = client.post(f"/documents/{doc_id}/delete")
    assert response.status_code == 403
