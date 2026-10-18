from datetime import datetime, timezone
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.documents import documents_bp
from app.extensions import db
from app.models import AuditEvent, Document
from app.utils import log_audit_event, verify_document_access

CATEGORIES = ["General", "Finance", "Legal", "Operations", "Engineering", "Human Resources"]


@documents_bp.route("", methods=["GET"])
@login_required
def list_documents():
    """List documents accessible to the current user with search, filter, and sorting."""
    user = current_user._get_current_object()
    query = Document.query

    # Apply role scoping
    if not user.is_admin:
        if user.is_reviewer:
            query = query.filter((Document.status != "draft") | (Document.owner_id == user.id))
        else:
            query = query.filter(Document.owner_id == user.id)

    # Search filter by title or content
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(Document.title.ilike(f"%{q}%"))

    # Status filter
    status = request.args.get("status", "").strip().lower()
    if status and status in ("draft", "pending_review", "approved", "rejected"):
        query = query.filter(Document.status == status)

    # Category filter
    category = request.args.get("category", "").strip()
    if category and category in CATEGORIES:
        query = query.filter(Document.category == category)

    # Sorting
    sort = request.args.get("sort", "newest").strip().lower()
    if sort == "oldest":
        query = query.order_by(Document.created_at.asc())
    elif sort == "title_asc":
        query = query.order_by(Document.title.asc())
    elif sort == "title_desc":
        query = query.order_by(Document.title.desc())
    else:  # newest
        query = query.order_by(Document.updated_at.desc())

    documents = query.all()

    return render_template(
        "documents/list.html",
        documents=documents,
        categories=CATEGORIES,
        q=q,
        selected_status=status,
        selected_category=category,
        selected_sort=sort,
    )


@documents_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_document():
    """Create a new document draft or submit immediately for review."""
    user = current_user._get_current_object()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        category = (request.form.get("category") or "General").strip()
        action = request.form.get("action", "save_draft").strip()

        if not title:
            flash("Document title is required.", "danger")
            return render_template("documents/new.html", title=title, content=content, category=category, categories=CATEGORIES)

        if len(title) > 200:
            flash("Title cannot exceed 200 characters.", "danger")
            return render_template("documents/new.html", title=title, content=content, category=category, categories=CATEGORIES)

        if not content:
            flash("Document content cannot be empty.", "danger")
            return render_template("documents/new.html", title=title, content=content, category=category, categories=CATEGORIES)

        if category not in CATEGORIES:
            category = "General"

        status = "pending_review" if action == "submit_review" else "draft"

        doc = Document(
            owner_id=user.id,
            title=title,
            content=content,
            category=category,
            status=status,
        )
        db.session.add(doc)
        db.session.commit()

        log_audit_event(
            event_type="doc.create",
            actor=user,
            object_type="document",
            object_id=doc.id,
            metadata={"title": doc.title, "status": doc.status, "category": doc.category},
        )

        if status == "pending_review":
            log_audit_event(
                event_type="doc.submit",
                actor=user,
                object_type="document",
                object_id=doc.id,
                metadata={"title": doc.title},
            )
            flash("Document submitted for review successfully!", "success")
        else:
            flash("Draft document saved successfully.", "success")

        return redirect(url_for("documents.view_document", id=doc.id))

    return render_template("documents/new.html", categories=CATEGORIES)


@documents_bp.route("/<int:id>", methods=["GET"])
@login_required
def view_document(id: int):
    """View document details, metadata, workflow state, history, and actions."""
    doc = db.get_or_404(Document, id)
    user = current_user._get_current_object()

    if not verify_document_access(doc, user, action="view"):
        abort(403)

    # Document-related audit events
    audit_events = (
        AuditEvent.query.filter_by(object_type="document", object_id=doc.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "documents/detail.html",
        doc=doc,
        audit_events=audit_events,
        can_edit=verify_document_access(doc, user, action="edit"),
        can_submit=verify_document_access(doc, user, action="submit"),
        can_delete=verify_document_access(doc, user, action="delete"),
        can_review=verify_document_access(doc, user, action="review"),
        can_process=verify_document_access(doc, user, action="process"),
    )


@documents_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_document(id: int):
    """Edit an existing document draft or rejected document."""
    doc = db.get_or_404(Document, id)
    user = current_user._get_current_object()

    if not verify_document_access(doc, user, action="edit"):
        abort(403)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        category = (request.form.get("category") or doc.category).strip()
        action = request.form.get("action", "save_draft").strip()

        if not title:
            flash("Document title is required.", "danger")
            return render_template("documents/edit.html", doc=doc, categories=CATEGORIES)

        if len(title) > 200:
            flash("Title cannot exceed 200 characters.", "danger")
            return render_template("documents/edit.html", doc=doc, categories=CATEGORIES)

        if not content:
            flash("Document content cannot be empty.", "danger")
            return render_template("documents/edit.html", doc=doc, categories=CATEGORIES)

        if category not in CATEGORIES:
            category = doc.category

        doc.title = title
        doc.content = content
        doc.category = category
        doc.updated_at = datetime.now(timezone.utc)

        if action == "submit_review":
            doc.status = "pending_review"
            log_audit_event(
                event_type="doc.submit",
                actor=user,
                object_type="document",
                object_id=doc.id,
                metadata={"title": doc.title, "note": "resubmitted_after_edit"},
            )
            flash("Document updated and submitted for review!", "success")
        else:
            flash("Document changes saved.", "success")

        log_audit_event(
            event_type="doc.update",
            actor=user,
            object_type="document",
            object_id=doc.id,
            metadata={"title": doc.title, "status": doc.status},
        )
        db.session.commit()

        return redirect(url_for("documents.view_document", id=doc.id))

    return render_template("documents/edit.html", doc=doc, categories=CATEGORIES)


@documents_bp.route("/<int:id>/submit", methods=["POST"])
@login_required
def submit_document(id: int):
    """Transition draft or rejected document into review queue."""
    doc = db.get_or_404(Document, id)
    user = current_user._get_current_object()

    if not verify_document_access(doc, user, action="submit"):
        abort(403)

    doc.status = "pending_review"
    doc.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    log_audit_event(
        event_type="doc.submit",
        actor=user,
        object_type="document",
        object_id=doc.id,
        metadata={"title": doc.title},
    )

    flash("Document has been submitted for review.", "success")
    return redirect(url_for("documents.view_document", id=doc.id))


@documents_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_document(id: int):
    """Delete draft document."""
    doc = db.get_or_404(Document, id)
    user = current_user._get_current_object()

    if not verify_document_access(doc, user, action="delete"):
        abort(403)

    doc_id = doc.id
    doc_title = doc.title

    db.session.delete(doc)
    db.session.commit()

    log_audit_event(
        event_type="doc.delete",
        actor=user,
        object_type="document",
        object_id=doc_id,
        metadata={"title": doc_title},
    )

    flash(f"Document '{doc_title}' was deleted successfully.", "info")
    return redirect(url_for("documents.list_documents"))
