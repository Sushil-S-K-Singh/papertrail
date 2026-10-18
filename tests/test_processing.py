import json
from app.extensions import db
from app.models import Document, ProcessingJob, User


def test_document_analysis_processing_job(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Statistical Document Test",
            content="The quick brown fox jumps over the lazy dog. Enterprise systems require continuous verification.",
            category="Engineering",
            status="approved",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")

    response = client.post(
        "/jobs/new",
        data={"document_id": doc_id, "job_type": "document_analysis"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"completed successfully" in response.data

    with app.app_context():
        job = ProcessingJob.query.filter_by(document_id=doc_id, job_type="document_analysis").first()
        assert job is not None
        assert job.status == "completed"
        assert job.completed_at is not None

        res = json.loads(job.result)
        assert res["word_count"] > 10
        assert res["character_count_total"] > 50
        assert "readability_index" in res


def test_checksum_verification_job(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Integrity Check Test",
            content="Cryptographic payload test.",
            category="Finance",
            status="approved",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")

    response = client.post(
        "/jobs/new",
        data={"document_id": doc_id, "job_type": "checksum_verify"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        job = ProcessingJob.query.filter_by(document_id=doc_id, job_type="checksum_verify").first()
        assert job.status == "completed"
        res = json.loads(job.result)
        assert len(res["sha256"]) == 64
        assert res["integrity_status"] == "Verified"


def test_compliance_audit_job_detects_pii(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="PII Exposure Test",
            content="CLASSIFICATION: CONFIDENTIAL\nEmployee SSN: 123-45-6789 and Card: 4111-2222-3333-4444.",
            category="Legal",
            status="pending_review",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("reviewer_user", "ReviewerPass123!")

    response = client.post(
        "/jobs/new",
        data={"document_id": doc_id, "job_type": "compliance_audit"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        job = ProcessingJob.query.filter_by(document_id=doc_id, job_type="compliance_audit").first()
        assert job.status == "completed"
        res = json.loads(job.result)
        assert res["pii_detected"] is True
        assert res["simulated_ssn_count"] == 1
        assert res["simulated_credit_card_count"] == 1
        assert "CONFIDENTIAL" in res["classification_labels_found"]


def test_redaction_preview_job(client, auth, app):
    with app.app_context():
        alice = User.query.filter_by(username="emp_alice").first()
        doc = Document(
            owner_id=alice.id,
            title="Redaction Test",
            content="Contact support@papertrail.corp or call 123-45-6789.",
            category="Operations",
            status="approved",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    auth.login("emp_alice", "EmployeePass123!")

    response = client.post(
        "/jobs/new",
        data={"document_id": doc_id, "job_type": "redaction_preview"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        job = ProcessingJob.query.filter_by(document_id=doc_id, job_type="redaction_preview").first()
        assert job.status == "completed"
        res = json.loads(job.result)
        assert "[REDACTED_EMAIL]" in res["redacted_preview"]
        assert "[REDACTED_SSN]" in res["redacted_preview"]
