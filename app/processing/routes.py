from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Document, ProcessingJob
from app.processing import processing_bp
from app.processing.processor import process_document_job
from app.utils import log_audit_event, verify_document_access

VALID_JOB_TYPES = {
    "document_analysis": "Document Statistics & Readability",
    "checksum_verify": "Cryptographic Integrity Check (SHA-256)",
    "compliance_audit": "Regulatory & PII Compliance Scan",
    "redaction_preview": "Data Sanitization & Redaction Preview",
}


@processing_bp.route("", methods=["GET"])
@login_required
def list_jobs():
    """List processing jobs with their execution state and results."""
    user = current_user._get_current_object()

    if user.is_admin or user.is_reviewer:
        jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).all()
        # Documents available to run jobs on
        available_docs = Document.query.filter(
            (Document.status != "draft") | (Document.owner_id == user.id)
        ).order_by(Document.title.asc()).all()
    else:
        jobs = (
            ProcessingJob.query.filter_by(requested_by=user.id)
            .order_by(ProcessingJob.created_at.desc())
            .all()
        )
        available_docs = (
            Document.query.filter_by(owner_id=user.id)
            .order_by(Document.title.asc())
            .all()
        )

    return render_template(
        "processing/list.html",
        jobs=jobs,
        available_docs=available_docs,
        job_types=VALID_JOB_TYPES,
    )


@processing_bp.route("/new", methods=["POST"])
@login_required
def create_job():
    """Trigger a new local document processing job."""
    user = current_user._get_current_object()

    doc_id = request.form.get("document_id")
    job_type = (request.form.get("job_type") or "document_analysis").strip()

    if not doc_id:
        flash("Please select a document to process.", "danger")
        return redirect(url_for("processing.list_jobs"))

    try:
        doc_id = int(doc_id)
    except ValueError:
        flash("Invalid document selected.", "danger")
        return redirect(url_for("processing.list_jobs"))

    doc = db.get_or_404(Document, doc_id)

    if not verify_document_access(doc, user, action="process"):
        abort(403)

    if job_type not in VALID_JOB_TYPES:
        flash("Invalid processing job type specified.", "danger")
        return redirect(url_for("processing.list_jobs"))

    # Create job in database
    job = ProcessingJob(
        document_id=doc.id,
        requested_by=user.id,
        job_type=job_type,
        status="pending",
    )
    db.session.add(job)
    db.session.commit()

    log_audit_event(
        event_type="job.create",
        actor=user,
        object_type="job",
        object_id=job.id,
        metadata={"job_type": job_type, "document_id": doc.id, "document_title": doc.title},
    )

    # Execute bounded processing
    completed_job = process_document_job(job.id)

    log_audit_event(
        event_type="job.complete",
        actor=user,
        object_type="job",
        object_id=job.id,
        metadata={"status": completed_job.status if completed_job else "failed"},
    )

    flash(f"Processing job #{job.id} ({VALID_JOB_TYPES.get(job_type)}) completed successfully!", "success")
    return redirect(url_for("processing.view_job", id=job.id))


@processing_bp.route("/<int:id>", methods=["GET"])
@login_required
def view_job(id: int):
    """View detailed execution log and JSON results of a processing job."""
    job = db.get_or_404(ProcessingJob, id)
    user = current_user._get_current_object()

    # Employees can only inspect jobs they requested or for their own documents
    if not (user.is_admin or user.is_reviewer):
        if job.requested_by != user.id and (job.document and job.document.owner_id != user.id):
            abort(403)

    return render_template(
        "processing/detail.html",
        job=job,
        job_type_label=VALID_JOB_TYPES.get(job.job_type, job.job_type),
    )
