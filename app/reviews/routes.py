from datetime import datetime, timezone
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from app.extensions import db
from app.models import Approval, AuditEvent, Document
from app.reviews import reviews_bp
from app.utils import log_audit_event, roles_required


@reviews_bp.route("", methods=["GET"])
@roles_required("reviewer", "admin")
def review_queue():
    """Review queue interface displaying pending submissions and past review history."""
    pending_docs = (
        Document.query.filter_by(status="pending_review")
        .order_by(Document.updated_at.asc())
        .all()
    )

    recent_approvals = (
        Approval.query.order_by(Approval.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "reviews/list.html",
        pending_docs=pending_docs,
        recent_approvals=recent_approvals,
    )


@reviews_bp.route("/<int:id>/decide", methods=["POST"])
@roles_required("reviewer", "admin")
def decide_review(id: int):
    """Approve or reject a submitted document."""
    doc = db.get_or_404(Document, id)
    user = current_user._get_current_object()

    # Workflow validation: only pending_review documents can be decided
    if doc.status != "pending_review":
        flash(f"Document is in status '{doc.status}' and cannot be reviewed.", "warning")
        return redirect(url_for("reviews.review_queue"))

    decision = (request.form.get("decision") or "").strip().lower()
    comments = (request.form.get("comments") or "").strip()

    if decision not in ("approved", "rejected"):
        flash("Invalid decision specified. Must be 'approved' or 'rejected'.", "danger")
        return redirect(url_for("documents.view_document", id=doc.id))

    # Record approval decision
    approval = Approval(
        document_id=doc.id,
        reviewer_id=user.id,
        decision=decision,
        comments=comments if comments else None,
    )
    db.session.add(approval)

    # Transition document status
    doc.status = decision
    doc.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    event_type = "review.approve" if decision == "approved" else "review.reject"
    log_audit_event(
        event_type=event_type,
        actor=user,
        object_type="document",
        object_id=doc.id,
        metadata={"decision": decision, "has_comment": bool(comments)},
    )

    action_label = "approved" if decision == "approved" else "rejected"
    flash(f"Document '{doc.title}' has been successfully {action_label}.", "success")
    return redirect(url_for("reviews.review_queue"))
