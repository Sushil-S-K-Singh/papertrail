from flask import render_template, request
from flask_login import current_user, login_required
from app.audit import audit_bp
from app.models import AuditEvent, Document


@audit_bp.route("", methods=["GET"])
@login_required
def list_audits():
    """System and user audit trail with event filtering."""
    user = current_user._get_current_object()
    query = AuditEvent.query

    # Role scoping
    if not user.is_admin:
        if user.is_reviewer:
            query = query.filter(
                (AuditEvent.actor_id == user.id)
                | (AuditEvent.event_type.like("review.%"))
                | (AuditEvent.event_type.like("doc.%"))
                | (AuditEvent.event_type.like("job.%"))
            )
        else:
            # Employee sees events they created or events affecting their documents
            user_doc_ids = [d.id for d in Document.query.filter_by(owner_id=user.id).all()]
            query = query.filter(
                (AuditEvent.actor_id == user.id)
                | ((AuditEvent.object_type == "document") & (AuditEvent.object_id.in_(user_doc_ids)))
            )

    # Filter by event type
    event_type = (request.args.get("event_type") or "").strip()
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)

    # Filter by object type
    object_type = (request.args.get("object_type") or "").strip()
    if object_type:
        query = query.filter(AuditEvent.object_type == object_type)

    events = query.order_by(AuditEvent.created_at.desc()).limit(100).all()

    # Distinct event types for dropdown
    available_event_types = [
        "auth.login_success",
        "auth.login_failure",
        "auth.logout",
        "auth.dev_register",
        "doc.create",
        "doc.update",
        "doc.submit",
        "doc.delete",
        "review.approve",
        "review.reject",
        "job.create",
        "job.complete",
        "admin.user_update",
    ]

    return render_template(
        "audit/index.html",
        events=events,
        selected_event_type=event_type,
        selected_object_type=object_type,
        available_event_types=available_event_types,
    )
