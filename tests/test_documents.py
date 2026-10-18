from app.extensions import db
from app.models import AuditEvent, Document, User


def test_create_draft_document(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")

    response = client.post(
        "/documents/new",
        data={
            "title": "Cloud Security Architecture Proposal",
            "category": "Engineering",
            "content": "This document specifies zero-trust security requirements.",
            "action": "save_draft",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Draft document saved successfully" in response.data
    assert b"Cloud Security Architecture Proposal" in response.data

    with app.app_context():
        doc = Document.query.filter_by(title="Cloud Security Architecture Proposal").first()
        assert doc is not None
        assert doc.status == "draft"
        assert doc.category == "Engineering"

        # Verify audit event
        audit = AuditEvent.query.filter_by(event_type="doc.create", object_id=doc.id).first()
        assert audit is not None


def test_create_and_submit_document(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")

    response = client.post(
        "/documents/new",
        data={
            "title": "Vendor SLA Review 2026",
            "category": "Legal",
            "content": "Service level agreement provisions for external cloud vendors.",
            "action": "submit_review",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Document submitted for review successfully" in response.data

    with app.app_context():
        doc = Document.query.filter_by(title="Vendor SLA Review 2026").first()
        assert doc is not None
        assert doc.status == "pending_review"


def test_create_document_validation(client, auth):
    auth.login("emp_alice", "EmployeePass123!")

    # Empty title
    response = client.post(
        "/documents/new",
        data={"title": "", "category": "General", "content": "Valid content"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Document title is required" in response.data

    # Empty content
    response = client.post(
        "/documents/new",
        data={"title": "Some Title", "category": "General", "content": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Document content cannot be empty" in response.data


def test_edit_draft_document(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")

    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Initial Title",
            content="Initial content",
            category="Finance",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    response = client.post(
        f"/documents/{doc_id}/edit",
        data={
            "title": "Updated Title",
            "category": "Finance",
            "content": "Updated content with additional details.",
            "action": "save_draft",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Document changes saved" in response.data

    with app.app_context():
        updated = db.session.get(Document, doc_id)
        assert updated.title == "Updated Title"
        assert updated.content == "Updated content with additional details."


def test_submit_draft_document(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")

    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Proposal Ready For Review",
            content="Complete text.",
            category="Operations",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    response = client.post(f"/documents/{doc_id}/submit", follow_redirects=True)
    assert response.status_code == 200
    assert b"Document has been submitted for review" in response.data

    with app.app_context():
        updated = db.session.get(Document, doc_id)
        assert updated.status == "pending_review"


def test_delete_draft_document(client, auth, app):
    auth.login("emp_alice", "EmployeePass123!")

    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Draft to Delete",
            content="Temporary draft.",
            category="General",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    response = client.post(f"/documents/{doc_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"deleted successfully" in response.data

    with app.app_context():
        assert db.session.get(Document, doc_id) is None


def test_search_and_filter_documents(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc1 = Document(owner_id=alice.id, title="Alpha Report", content="Alpha", category="Finance", status="approved")
        doc2 = Document(owner_id=alice.id, title="Beta Report", content="Beta", category="Legal", status="draft")
        db.session.add_all([doc1, doc2])
        db.session.commit()

    auth.login("emp_alice", "EmployeePass123!")

    # Search for Alpha
    res = client.get("/documents?q=Alpha")
    assert b"Alpha Report" in res.data
    assert b"Beta Report" not in res.data

    # Filter by category Finance
    res_cat = client.get("/documents?category=Finance")
    assert b"Alpha Report" in res_cat.data
    assert b"Beta Report" not in res_cat.data

    # Filter by status draft
    res_status = client.get("/documents?status=draft")
    assert b"Beta Report" in res_status.data
    assert b"Alpha Report" not in res_status.data
