import os
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from app.admin import admin_bp
from app.extensions import db
from app.models import Approval, AuditEvent, Document, ProcessingJob, User
from app.utils import log_audit_event, roles_required


@admin_bp.route("", methods=["GET"])
@roles_required("admin")
def dashboard():
    """Administrator control center with system overview, telemetry, and user management."""
    users = User.query.order_by(User.id.asc()).all()
    total_docs = Document.query.count()
    pending_reviews = Document.query.filter_by(status="pending_review").count()
    total_approvals = Approval.query.count()
    
    total_jobs = ProcessingJob.query.count()
    completed_jobs = ProcessingJob.query.filter_by(status="completed").count()
    failed_jobs = ProcessingJob.query.filter_by(status="failed").count()

    recent_audits = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(15).all()

    # System & Challenge telemetry
    challenge_mode = current_app.config.get("CHALLENGE_MODE", False)
    challenge_flag = current_app.config.get("CHALLENGE_FLAG", "FLAG{papertrail_enterprise_workflow_audit_passed_2026}")

    stats = {
        "total_users": len(users),
        "total_documents": total_docs,
        "pending_reviews": pending_reviews,
        "total_approvals": total_approvals,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
    }

    return render_template(
        "admin/index.html",
        stats=stats,
        users=users,
        recent_audits=recent_audits,
        challenge_mode=challenge_mode,
        challenge_flag=challenge_flag,
    )


@admin_bp.route("/users/<int:id>/toggle-active", methods=["POST"])
@roles_required("admin")
def toggle_user_active(id: int):
    """Toggle user active / suspended status."""
    user = db.get_or_404(User, id)
    admin = current_user._get_current_object()

    if user.id == admin.id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for("admin.dashboard"))

    user.active = not user.active
    db.session.commit()

    action_label = "activated" if user.active else "deactivated"
    log_audit_event(
        event_type="admin.user_update",
        actor=admin,
        object_type="user",
        object_id=user.id,
        metadata={"target_user": user.username, "active": user.active, "action": action_label},
    )

    flash(f"User '{user.username}' has been {action_label}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:id>/change-role", methods=["POST"])
@roles_required("admin")
def change_user_role(id: int):
    """Change user role (employee, reviewer, admin)."""
    user = db.get_or_404(User, id)
    admin = current_user._get_current_object()

    new_role = (request.form.get("role") or "").strip().lower()
    if new_role not in ("employee", "reviewer", "admin"):
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin.dashboard"))

    if user.id == admin.id and new_role != "admin":
        flash("You cannot remove your own administrator role.", "danger")
        return redirect(url_for("admin.dashboard"))

    old_role = user.role
    user.role = new_role
    db.session.commit()

    log_audit_event(
        event_type="admin.user_update",
        actor=admin,
        object_type="user",
        object_id=user.id,
        metadata={"target_user": user.username, "old_role": old_role, "new_role": new_role},
    )

    flash(f"Role for '{user.username}' changed from {old_role} to {new_role}.", "success")
    return redirect(url_for("admin.dashboard"))
