from flask import jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import func, select
from app.dashboard import dashboard_bp
from app.extensions import db
from app.models import AuditEvent, Document, ProcessingJob, User


@dashboard_bp.route("/")
def landing():
    """Public marketing landing page."""
    return render_template("landing.html")


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Main authenticated role-based dashboard."""
    user = current_user._get_current_object()

    if user.is_admin:
        # Admin statistics across whole platform
        total_docs = Document.query.count()
        draft_docs = Document.query.filter_by(status="draft").count()
        pending_docs = Document.query.filter_by(status="pending_review").count()
        approved_docs = Document.query.filter_by(status="approved").count()
        rejected_docs = Document.query.filter_by(status="rejected").count()

        recent_docs = Document.query.order_by(Document.updated_at.desc()).limit(6).all()
        recent_audits = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(6).all()
        total_users = User.query.count()
        total_jobs = ProcessingJob.query.count()

    elif user.is_reviewer:
        # Reviewer view: review queue priority + system approved/rejected
        total_docs = Document.query.filter(
            (Document.status != "draft") | (Document.owner_id == user.id)
        ).count()
        draft_docs = Document.query.filter_by(owner_id=user.id, status="draft").count()
        pending_docs = Document.query.filter_by(status="pending_review").count()
        approved_docs = Document.query.filter_by(status="approved").count()
        rejected_docs = Document.query.filter_by(status="rejected").count()

        recent_docs = (
            Document.query.filter((Document.status != "draft") | (Document.owner_id == user.id))
            .order_by(Document.updated_at.desc())
            .limit(6)
            .all()
        )
        recent_audits = (
            AuditEvent.query.filter(
                (AuditEvent.actor_id == user.id)
                | (AuditEvent.event_type.like("review.%"))
                | (AuditEvent.event_type.like("doc.%"))
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(6)
            .all()
        )
        total_users = None
        total_jobs = ProcessingJob.query.count()

    else:
        # Employee view: scoped strictly to employee's own documents
        total_docs = Document.query.filter_by(owner_id=user.id).count()
        draft_docs = Document.query.filter_by(owner_id=user.id, status="draft").count()
        pending_docs = Document.query.filter_by(owner_id=user.id, status="pending_review").count()
        approved_docs = Document.query.filter_by(owner_id=user.id, status="approved").count()
        rejected_docs = Document.query.filter_by(owner_id=user.id, status="rejected").count()

        recent_docs = (
            Document.query.filter_by(owner_id=user.id)
            .order_by(Document.updated_at.desc())
            .limit(6)
            .all()
        )
        recent_audits = (
            AuditEvent.query.filter(
                (AuditEvent.actor_id == user.id)
                | ((AuditEvent.object_type == "document") & (AuditEvent.object_id.in_([d.id for d in recent_docs])))
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(6)
            .all()
        )
        total_users = None
        total_jobs = ProcessingJob.query.filter_by(requested_by=user.id).count()

    stats = {
        "total": total_docs,
        "draft": draft_docs,
        "pending": pending_docs,
        "approved": approved_docs,
        "rejected": rejected_docs,
        "users": total_users,
        "jobs": total_jobs,
    }

    return render_template(
        "dashboard/index.html",
        stats=stats,
        recent_docs=recent_docs,
        recent_audits=recent_audits,
    )


@dashboard_bp.route("/health")
def health():
    """Health check endpoint confirming web server and database accessibility."""
    try:
        # Execute minimal database verification query
        db.session.execute(select(1)).scalar()
        db_status = "connected"
        status_code = 200
        status_text = "ok"
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"
        status_code = 503
        status_text = "error"

    return (
        jsonify({
            "status": status_text,
            "database": db_status,
            "service": "PaperTrail Document Approval Portal",
            "version": "1.0.0",
        }),
        status_code,
    )
