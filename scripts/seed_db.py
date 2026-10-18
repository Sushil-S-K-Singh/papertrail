import json
import os
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import Approval, AuditEvent, Document, ProcessingJob, User
from app.processing.processor import process_document_job


def seed_db():
    """Seeds the database with deterministic synthetic test records."""
    app = create_app()
    with app.app_context():
        print("[*] Ensuring database tables exist...")
        db.create_all()

        base_time = datetime(2026, 10, 10, 9, 0, 0, tzinfo=timezone.utc)

        # 1. Seed Users
        users_def = [
            ("admin", os.environ.get("PAPERTRAIL_ADMIN_PASS", "AdminSecure2026!"), "admin"),
            ("rachel_rev", "ReviewerPass123!", "reviewer"),
            ("victor_rev", "ReviewerPass123!", "reviewer"),
            ("alice_emp", "EmployeePass123!", "employee"),
            ("bob_emp", "EmployeePass123!", "employee"),
            ("carol_emp", "EmployeePass123!", "employee"),
        ]

        users = {}
        for username, password, role in users_def:
            u = User.query.filter_by(username=username).first()
            if not u:
                u = User(
                    username=username,
                    role=role,
                    active=True,
                    created_at=base_time - timedelta(days=30),
                )
                u.set_password(password)
                db.session.add(u)
                db.session.flush()
                print(f"  [+] Created user: {username} ({role})")
            else:
                # Update role and ensure password
                u.role = role
                u.active = True
                u.set_password(password)
            users[username] = u

        db.session.commit()

        # 2. Seed Documents
        docs_def = [
            {
                "title": "Q3 Infrastructure Modernization Proposal",
                "owner": "alice_emp",
                "category": "Engineering",
                "status": "draft",
                "content": (
                    "PROPOSAL: Q3 INFRASTRUCTURE UPGRADE\n\n"
                    "1. Executive Summary\n"
                    "This proposal outlines the timeline and budget to migrate our legacy application nodes "
                    "to a containerized architecture on modern virtualized Linux host clusters.\n\n"
                    "2. Scope and Objectives\n"
                    "- Reduce cold restart latency by 65%\n"
                    "- Implement automated rolling updates with health checks\n"
                    "- Isolate database volume mounts with strict DAC permissions\n\n"
                    "3. Estimated Budget\n"
                    "Hardware allocations: $14,500. Professional services: $8,000. Total: $22,500.\n"
                ),
                "created_offset_days": 5,
            },
            {
                "title": "Vendor Onboarding Guidelines 2026",
                "owner": "bob_emp",
                "category": "Operations",
                "status": "draft",
                "content": (
                    "STANDARD OPERATING PROCEDURE: VENDOR ONBOARDING\n\n"
                    "Objective: Establish a rigorous evaluation procedure for third-party service providers.\n\n"
                    "Requirements:\n"
                    "1. Proof of SOC-2 Type II or ISO 27001 certification.\n"
                    "2. Mandatory Non-Disclosure Agreement (NDA) executed before technical discovery.\n"
                    "3. Security questionnaire completion and review by IT Operations.\n"
                    "4. Data retention and scheduled purge agreement.\n"
                ),
                "created_offset_days": 4,
            },
            {
                "title": "Corporate Expense and Travel Policy Update",
                "owner": "alice_emp",
                "category": "Finance",
                "status": "pending_review",
                "content": (
                    "POLICY DOCUMENT: CORPORATE TRAVEL & REIMBURSEMENTS\n\n"
                    "Classification: INTERNAL ONLY\n\n"
                    "1. Overview\n"
                    "This updated policy governs all business-related travel, lodging, and client entertainment "
                    "incurred by full-time personnel on behalf of PaperTrail Corp.\n\n"
                    "2. Expense Limits\n"
                    "- Domestic flights: Economy class required for routes under 5 hours.\n"
                    "- Hotel per diem: Maximum $220/night inclusive of city taxes.\n"
                    "- Meal allowance: $75 per day aggregate, itemized receipts required.\n\n"
                    "3. Approval Hierarchy\n"
                    "Expenses over $1,000 require secondary managerial sign-off prior to booking."
                ),
                "created_offset_days": 3,
            },
            {
                "title": "Client Data Protection Agreement Addendum",
                "owner": "carol_emp",
                "category": "Legal",
                "status": "pending_review",
                "content": (
                    "ADDENDUM TO MASTER SERVICES AGREEMENT: DATA PRIVACY & COMPLIANCE\n\n"
                    "Classification: CONFIDENTIAL & PROPRIETARY\n\n"
                    "1. Background\n"
                    "Pursuant to applicable data protection regulations (GDPR and CCPA), this addendum clarifies "
                    "data processor obligations regarding customer personal identifiable information.\n\n"
                    "2. Processing Guardrails\n"
                    "- Data must be encrypted at rest using AES-256 GCM.\n"
                    "- Sub-processors may only be engaged upon 30 days prior written notification.\n"
                    "- Incident notification window is capped at 48 hours post-discovery.\n"
                ),
                "created_offset_days": 2,
            },
            {
                "title": "Annual Remote Work and Equipment Stipend Policy",
                "owner": "bob_emp",
                "category": "Human Resources",
                "status": "approved",
                "content": (
                    "HUMAN RESOURCES POLICY: WORK FROM HOME (WFH) STIPEND\n\n"
                    "Classification: INTERNAL USE ONLY\n\n"
                    "Section A: Equipment Allocation\n"
                    "Each eligible employee receives an annual $750 ergonomic and hardware stipend to maintain "
                    "a safe and productive home workstation.\n\n"
                    "Section B: Reimbursement Workflow\n"
                    "Invoices must be submitted through the portal within 30 days of purchase with vendor receipts.\n"
                ),
                "created_offset_days": 7,
                "approval": {
                    "reviewer": "rachel_rev",
                    "decision": "approved",
                    "comments": "Reviewed with People Ops. Clear definitions and standard limits. Approved for rollout.",
                    "offset_days": 6,
                },
            },
            {
                "title": "Quarterly Financial Audit and Disclosures Q1-2026",
                "owner": "alice_emp",
                "category": "Finance",
                "status": "approved",
                "content": (
                    "FINANCIAL DISCLOSURE: Q1 2026 CONSOLIDATED SUMMARY\n\n"
                    "Classification: RESTRICTED\n\n"
                    "Summary Figures:\n"
                    "- Gross Revenue: $4,280,000\n"
                    "- Operating Expenses: $2,950,000\n"
                    "- Net Margin: 31.07%\n\n"
                    "Auditor Notes:\n"
                    "Independent audit completed with zero material discrepancies reported. "
                    "Tax provision adjustments have been recognized in line with statutory filing guidelines."
                ),
                "created_offset_days": 10,
                "approval": {
                    "reviewer": "victor_rev",
                    "decision": "approved",
                    "comments": "All figures cross-referenced against treasury reconciliations. Approved without condition.",
                    "offset_days": 8,
                },
            },
            {
                "title": "Unrestricted Cloud Storage Provisioning Request",
                "owner": "carol_emp",
                "category": "Engineering",
                "status": "rejected",
                "content": (
                    "PROVISIONING REQUEST: PUBLIC OBJECT STORAGE BUCKETS\n\n"
                    "Requesting public read ACL on s3-export-staging bucket to facilitate external tester file sharing.\n"
                    "Data contains build artifacts and diagnostic logs.\n"
                ),
                "created_offset_days": 6,
                "approval": {
                    "reviewer": "rachel_rev",
                    "decision": "rejected",
                    "comments": "Denied. Unrestricted public ACL violates PaperTrail information security policy. Please use presigned URLs with 15-minute expirations instead.",
                    "offset_days": 5,
                },
            },
        ]

        created_docs = {}
        for d in docs_def:
            doc = Document.query.filter_by(title=d["title"]).first()
            owner = users[d["owner"]]
            doc_created_at = base_time - timedelta(days=d["created_offset_days"])

            if not doc:
                doc = Document(
                    title=d["title"],
                    owner_id=owner.id,
                    category=d["category"],
                    status=d["status"],
                    content=d["content"],
                    created_at=doc_created_at,
                    updated_at=doc_created_at,
                )
                db.session.add(doc)
                db.session.flush()
                print(f"  [+] Created document: {doc.title} ({doc.status})")

                # Initial creation audit
                AuditEvent.query.filter_by(
                    event_type="doc.create", object_id=doc.id
                ).delete()
                db.session.add(
                    AuditEvent(
                        actor_id=owner.id,
                        event_type="doc.create",
                        object_type="document",
                        object_id=doc.id,
                        metadata_json=json.dumps({"title": doc.title, "status": doc.status}),
                        created_at=doc_created_at,
                    )
                )

                if doc.status in ("pending_review", "approved", "rejected"):
                    db.session.add(
                        AuditEvent(
                            actor_id=owner.id,
                            event_type="doc.submit",
                            object_type="document",
                            object_id=doc.id,
                            metadata_json=json.dumps({"title": doc.title}),
                            created_at=doc_created_at + timedelta(hours=1),
                        )
                    )

            # Approvals
            if "approval" in d:
                appr_data = d["approval"]
                rev_user = users[appr_data["reviewer"]]
                existing_appr = Approval.query.filter_by(
                    document_id=doc.id, reviewer_id=rev_user.id
                ).first()
                if not existing_appr:
                    appr_time = base_time - timedelta(days=appr_data["offset_days"])
                    appr = Approval(
                        document_id=doc.id,
                        reviewer_id=rev_user.id,
                        decision=appr_data["decision"],
                        comments=appr_data["comments"],
                        created_at=appr_time,
                    )
                    db.session.add(appr)
                    db.session.add(
                        AuditEvent(
                            actor_id=rev_user.id,
                            event_type=(
                                "review.approve"
                                if appr_data["decision"] == "approved"
                                else "review.reject"
                            ),
                            object_type="document",
                            object_id=doc.id,
                            metadata_json=json.dumps({"decision": appr_data["decision"]}),
                            created_at=appr_time,
                        )
                    )
                    print(f"  [+] Added approval decision for doc #{doc.id}: {appr_data['decision']}")

            created_docs[d["title"]] = doc

        db.session.commit()

        # 3. Seed Processing Jobs
        job_docs = [
            ("Quarterly Financial Audit and Disclosures Q1-2026", "document_analysis", "alice_emp"),
            ("Client Data Protection Agreement Addendum", "compliance_audit", "carol_emp"),
            ("Corporate Expense and Travel Policy Update", "checksum_verify", "alice_emp"),
        ]

        for doc_title, j_type, req_user in job_docs:
            if doc_title in created_docs:
                target_doc = created_docs[doc_title]
                req = users[req_user]
                existing_job = ProcessingJob.query.filter_by(
                    document_id=target_doc.id, job_type=j_type
                ).first()

                if not existing_job:
                    job = ProcessingJob(
                        document_id=target_doc.id,
                        requested_by=req.id,
                        job_type=j_type,
                        status="pending",
                        created_at=base_time - timedelta(days=1),
                    )
                    db.session.add(job)
                    db.session.commit()
                    # Execute real processing
                    process_document_job(job.id)
                    print(f"  [+] Executed processing job for doc #{target_doc.id} ({j_type})")

        # 4. Add Baseline System / Auth Audit Events
        if AuditEvent.query.filter_by(event_type="auth.login_success").count() == 0:
            events_to_add = [
                (users["admin"].id, "auth.login_success", "user", users["admin"].id, {"role": "admin", "ip": "127.0.0.1"}),
                (users["rachel_rev"].id, "auth.login_success", "user", users["rachel_rev"].id, {"role": "reviewer", "ip": "127.0.0.1"}),
                (users["alice_emp"].id, "auth.login_success", "user", users["alice_emp"].id, {"role": "employee", "ip": "127.0.0.1"}),
                (None, "auth.login_failure", "user", None, {"attempted_username": "intruder", "reason": "invalid_credentials", "ip": "192.168.1.100"}),
            ]
            for act_id, ev_type, obj_type, obj_id, meta in events_to_add:
                db.session.add(
                    AuditEvent(
                        actor_id=act_id,
                        event_type=ev_type,
                        object_type=obj_type,
                        object_id=obj_id,
                        metadata_json=json.dumps(meta),
                        created_at=base_time - timedelta(days=2),
                    )
                )
            db.session.commit()

        print("[+] Deterministic synthetic seed data loaded successfully!")


if __name__ == "__main__":
    seed_db()
