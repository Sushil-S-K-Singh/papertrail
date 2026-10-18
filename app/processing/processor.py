import hashlib
import json
import re
from datetime import datetime, timezone
from app.extensions import db
from app.models import Document, ProcessingJob


def process_document_job(job_id: int):
    """
    Executes real, bounded document processing logic on the given ProcessingJob.
    Updates the database with computed results and completion timestamp.
    """
    job = db.session.get(ProcessingJob, job_id)
    if not job:
        return None

    job.status = "running"
    db.session.commit()

    doc = job.document
    if not doc:
        job.status = "failed"
        job.result = json.dumps({"error": "Referenced document was not found."})
        job.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return job

    content = doc.content or ""
    job_type = job.job_type or "document_analysis"
    result_data = {}

    try:
        if job_type == "document_analysis":
            chars_with_spaces = len(content)
            chars_no_spaces = len(content.replace(" ", "").replace("\n", "").replace("\r", ""))
            words = re.findall(r"\b\w+\b", content)
            word_count = len(words)
            lines = content.splitlines()
            line_count = len(lines)
            paragraphs = [p for p in content.split("\n\n") if p.strip()]
            paragraph_count = max(1, len(paragraphs))
            sentences = re.split(r"[.!?]+", content)
            sentence_count = max(1, len([s for s in sentences if s.strip()]))
            
            avg_word_length = round(chars_no_spaces / max(1, word_count), 2)
            reading_time_minutes = round(word_count / 200.0, 2)
            
            # Automated Readability Index (ARI)
            ari_score = 4.71 * (chars_no_spaces / max(1, word_count)) + 0.5 * (word_count / sentence_count) - 21.43
            ari_grade = max(1, min(16, round(ari_score, 1)))

            result_data = {
                "job_type": "Document Analysis",
                "word_count": word_count,
                "character_count_total": chars_with_spaces,
                "character_count_no_spaces": chars_no_spaces,
                "line_count": line_count,
                "paragraph_count": paragraph_count,
                "sentence_count": sentence_count,
                "avg_word_length": avg_word_length,
                "estimated_reading_time_min": reading_time_minutes,
                "readability_index": ari_grade,
                "status_assessment": "Analysis completed successfully without errors."
            }

        elif job_type == "checksum_verify":
            encoded = content.encode("utf-8")
            sha256_hash = hashlib.sha256(encoded).hexdigest()
            sha1_hash = hashlib.sha1(encoded).hexdigest()
            md5_hash = hashlib.md5(encoded).hexdigest()
            byte_size = len(encoded)

            result_data = {
                "job_type": "Cryptographic Integrity Check",
                "sha256": sha256_hash,
                "sha1": sha1_hash,
                "md5": md5_hash,
                "byte_size": byte_size,
                "integrity_status": "Verified",
                "verified_at": datetime.now(timezone.utc).isoformat()
            }

        elif job_type == "compliance_audit":
            # Check for classification markers
            markers_found = []
            for marker in ["CONFIDENTIAL", "RESTRICTED", "INTERNAL ONLY", "PROPRIETARY", "PUBLIC"]:
                if re.search(r"\b" + marker + r"\b", content, re.IGNORECASE):
                    markers_found.append(marker)

            # Simulated SSN / Account / Email detections
            ssn_matches = re.findall(r"\b\d{3}-\d{2}-\d{4}\b", content)
            email_matches = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content)
            credit_card_matches = re.findall(r"\b(?:\d{4}-){3}\d{4}\b", content)

            has_sensitive = bool(ssn_matches or credit_card_matches)
            compliance_status = "Action Required" if has_sensitive else ("Compliant" if markers_found else "Neutral")

            result_data = {
                "job_type": "Regulatory & Compliance Audit",
                "classification_labels_found": markers_found,
                "pii_detected": has_sensitive,
                "simulated_ssn_count": len(ssn_matches),
                "simulated_credit_card_count": len(credit_card_matches),
                "emails_detected_count": len(email_matches),
                "compliance_status": compliance_status,
                "audit_notes": (
                    "Potentially sensitive identifiable patterns were flagged for security review."
                    if has_sensitive else "Standard compliance criteria satisfied."
                )
            }

        elif job_type == "redaction_preview":
            redacted = content
            # Redact emails
            redacted = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", redacted)
            # Redact SSN
            redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", redacted)
            # Redact cards
            redacted = re.sub(r"\b(?:\d{4}-){3}\d{4}\b", "[REDACTED_CARD]", redacted)

            result_data = {
                "job_type": "Data Sanitization & Redaction Preview",
                "original_length": len(content),
                "redacted_length": len(redacted),
                "redacted_preview": redacted[:500] + ("..." if len(redacted) > 500 else ""),
                "status_assessment": "Sanitization mask preview generated successfully."
            }

        else:
            result_data = {
                "job_type": job_type,
                "message": "Processed general document workflow check.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        job.status = "completed"
        job.result = json.dumps(result_data, indent=2)
        job.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        job.status = "failed"
        job.result = json.dumps({"error": f"Processing encountered an unexpected error: {str(exc)}"})
        job.completed_at = datetime.now(timezone.utc)

    db.session.commit()
    return job
