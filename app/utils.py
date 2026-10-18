import json
from functools import wraps
from flask import abort, flash, redirect, request, url_for
from flask_login import current_user
from app.extensions import db
from app.models import AuditEvent, Document


def roles_required(*roles):
    """
    Decorator enforcing that the logged-in user belongs to one of the specified roles.
    If unauthenticated, redirects to login.
    If authenticated but role not allowed, aborts with 403 Forbidden.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def verify_document_access(document: Document, user, action="view") -> bool:
    """
    Evaluates whether the given user can perform the specified action on the document:
    - 'view': Owner, Reviewer (if not draft), Admin. (Drafts are strictly private to owner & admin)
    - 'edit': Owner (if draft or rejected) or Admin.
    - 'submit': Owner (if draft or rejected) or Admin.
    - 'review': Reviewer or Admin (if pending_review).
    - 'delete': Owner (if draft) or Admin.
    - 'process': Owner, Reviewer, or Admin (if not draft).
    """
    if not user.is_authenticated:
        return False
    
    if user.is_admin:
        return True

    if action == "view":
        # Owner can view all their documents
        if document.owner_id == user.id:
            return True
        # Reviewers can view submitted or finalized documents
        if user.is_reviewer and document.status in ("pending_review", "approved", "rejected"):
            return True
        return False

    elif action in ("edit", "submit"):
        return document.owner_id == user.id and document.status in ("draft", "rejected")

    elif action == "delete":
        return document.owner_id == user.id and document.status == "draft"

    elif action == "review":
        return user.is_reviewer and document.status == "pending_review"

    elif action == "process":
        # Processing is allowed on reviewed documents (pending_review, approved, rejected) or by owner
        if document.owner_id == user.id:
            return True
        if user.is_reviewer and document.status != "draft":
            return True
        return False

    return False


def log_audit_event(event_type: str, actor=None, object_type: str = None, object_id: int = None, metadata: dict = None):
    """
    Safely records an audit event into the database.
    Does NOT log passwords, tokens, or sensitive credentials.
    """
    try:
        actor_id = None
        if actor and getattr(actor, "is_authenticated", False):
            actor_id = actor.id
        elif current_user and current_user.is_authenticated:
            actor_id = current_user.id

        # Clean metadata to prevent sensitive keys
        clean_meta = {}
        if metadata:
            for k, v in metadata.items():
                if any(bad in k.lower() for bad in ("password", "token", "secret", "cookie", "auth")):
                    continue
                clean_meta[k] = v

        # Add client IP and user agent if inside request context
        if request:
            clean_meta["ip"] = request.remote_addr or "127.0.0.1"

        meta_json = json.dumps(clean_meta) if clean_meta else None

        event = AuditEvent(
            actor_id=actor_id,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            metadata_json=meta_json,
        )
        db.session.add(event)
        db.session.commit()
        return event
    except Exception as e:
        db.session.rollback()
        # Non-fatal error so application operations are not broken by audit failure
        return None
