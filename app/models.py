import json
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


def get_utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee", index=True)  # employee, reviewer, admin
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    # Relationships
    documents = db.relationship("Document", back_populates="owner", cascade="all, delete-orphan", lazy="dynamic")
    approvals = db.relationship("Approval", back_populates="reviewer", lazy="dynamic")
    jobs = db.relationship("ProcessingJob", back_populates="requester", lazy="dynamic")
    audit_events = db.relationship("AuditEvent", back_populates="actor", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_reviewer(self):
        return self.role in ("reviewer", "admin")

    @property
    def is_employee(self):
        return self.role == "employee"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="General", index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)  # draft, pending_review, approved, rejected
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    owner = db.relationship("User", back_populates="documents")
    approvals = db.relationship("Approval", back_populates="document", cascade="all, delete-orphan", order_by="Approval.created_at.desc()")
    jobs = db.relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan", order_by="ProcessingJob.created_at.desc()")

    @property
    def latest_approval(self):
        return self.approvals[0] if self.approvals else None

    def can_edit(self, user):
        """User can edit if they are the owner and doc is draft or rejected (or admin)."""
        if not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        return self.owner_id == user.id and self.status in ("draft", "rejected")

    def can_submit(self, user):
        """User can submit if they are owner and status is draft or rejected."""
        if not user.is_authenticated:
            return False
        if user.is_admin:
            return self.status in ("draft", "rejected")
        return self.owner_id == user.id and self.status in ("draft", "rejected")

    def can_review(self, user):
        """Reviewers and admins can review pending documents."""
        if not user.is_authenticated:
            return False
        return user.is_reviewer and self.status == "pending_review"

    def can_delete(self, user):
        """Owner can delete draft documents. Admins can delete any."""
        if not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        return self.owner_id == user.id and self.status == "draft"

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "owner_name": self.owner.username if self.owner else None,
            "title": self.title,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Document {self.id}: {self.title} [{self.status}]>"


class Approval(db.Model):
    __tablename__ = "approvals"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    decision = db.Column(db.String(20), nullable=False)  # approved, rejected
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    # Relationships
    document = db.relationship("Document", back_populates="approvals")
    reviewer = db.relationship("User", back_populates="approvals")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer.username if self.reviewer else None,
            "decision": self.decision,
            "comments": self.comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Approval doc={self.document_id} by={self.reviewer_id} {self.decision}>"


class ProcessingJob(db.Model):
    __tablename__ = "processing_jobs"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    job_type = db.Column(db.String(50), nullable=False, default="document_analysis")
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    result = db.Column(db.Text, nullable=True)  # JSON text
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    document = db.relationship("Document", back_populates="jobs")
    requester = db.relationship("User", back_populates="jobs")

    @property
    def result_data(self):
        if not self.result:
            return {}
        try:
            return json.loads(self.result)
        except Exception:
            return {"raw": self.result}

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_title": self.document.title if self.document else None,
            "requested_by": self.requested_by,
            "requester_name": self.requester.username if self.requester else None,
            "job_type": self.job_type,
            "status": self.status,
            "result": self.result_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return f"<ProcessingJob {self.id} doc={self.document_id} status={self.status}>"


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    object_type = db.Column(db.String(50), nullable=True, index=True)
    object_id = db.Column(db.Integer, nullable=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now, index=True)

    # Relationships
    actor = db.relationship("User", back_populates="audit_events")

    @property
    def details(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {"raw": self.metadata_json}

    def to_dict(self):
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_name": self.actor.username if self.actor else "System/Anonymous",
            "event_type": self.event_type,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "metadata": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AuditEvent {self.id}: {self.event_type} by={self.actor_id}>"
