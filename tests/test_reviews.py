from app.extensions import db
from app.models import Approval, AuditEvent, Document, User


def test_reviewer_can_view_review_queue(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Policy Waiting For Review",
            content="Policy text.",
            category="Legal",
            status="pending_review",
        )
        db.session.add(doc)
        db.session.commit()

    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.get("/reviews")
    assert response.status_code == 200
    assert b"Document Review Queue" in response.data
    assert b"Policy Waiting For Review" in response.data


def test_reviewer_can_approve_document(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Budget Proposal",
            content="Numbers and balance.",
            category="Finance",
            status="pending_review",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.post(
        f"/reviews/{doc_id}/decide",
        data={"decision": "approved", "comments": "Budget is sound and compliant."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"approved" in response.data

    with app.app_context():
        updated = db.session.get(Document, doc_id)
        assert updated.status == "approved"
        appr = Approval.query.filter_by(document_id=doc_id).first()
        assert appr is not None
        assert appr.decision == "approved"
        assert appr.comments == "Budget is sound and compliant."

        audit = AuditEvent.query.filter_by(event_type="review.approve", object_id=doc_id).first()
        assert audit is not None


def test_reviewer_can_reject_document(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Non-compliant Contract",
            content="Terms are unacceptable.",
            category="Legal",
            status="pending_review",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.post(
        f"/reviews/{doc_id}/decide",
        data={"decision": "rejected", "comments": "Indemnification clause is missing."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"rejected" in response.data

    with app.app_context():
        updated = db.session.get(Document, doc_id)
        assert updated.status == "rejected"


def test_cannot_review_draft_document(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Draft Incomplete",
            content="WIP",
            category="General",
            status="draft",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("reviewer_user", "ReviewerPass123!")
    response = client.post(
        f"/reviews/{doc_id}/decide",
        data={"decision": "approved", "comments": "Looks good"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"cannot be reviewed" in response.data

    with app.app_context():
        updated = db.session.get(Document, doc_id)
        assert updated.status == "draft"


def test_employee_cannot_decide_review(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Pending Proposal",
            content="WIP",
            category="General",
            status="pending_review",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_bob", "EmployeePass123!")
    response = client.post(
        f"/reviews/{doc_id}/decide",
        data={"decision": "approved", "comments": "Self approval attempt"},
    )
    assert response.status_code == 403
