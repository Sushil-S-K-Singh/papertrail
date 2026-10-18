# PaperTrail — Architecture & Security Specification

This document details the architectural boundaries, security design, workflow state transitions, and database schema for the PaperTrail enterprise document approval platform.

---

## 1. Architectural Overview

PaperTrail is structured as a modular Flask application using the Application Factory pattern (`create_app`) and Flask Blueprints. It enforces strict separation of concerns across authentication, document management, peer review, processing jobs, administrative governance, and audit logging.

```text
                           ┌───────────────────────────┐
                           │   Client (Web Browser)    │
                           └─────────────┬─────────────┘
                                         │ HTTP(S) / Cookie Session
                                         ▼
                           ┌───────────────────────────┐
                           │   PaperTrail Application  │
                           │      (Flask 3.1.3)        │
                           └─────────────┬─────────────┘
                                         │
        ┌───────────────┬────────────────┼───────────────┬───────────────┐
        ▼               ▼                ▼               ▼               ▼
  ┌───────────┐   ┌───────────┐    ┌───────────┐   ┌───────────┐   ┌───────────┐
  │   Auth    │   │ Documents │    │  Reviews  │   │Processing │   │   Admin   │
  │ Blueprint │   │ Blueprint │    │ Blueprint │   │ Blueprint │   │ Blueprint │
  └─────┬─────┘   └─────┬─────┘    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
        │               │                │               │               │
        └───────────────┴────────────────┼───────────────┴───────────────┘
                                         ▼
                           ┌───────────────────────────┐
                           │   SQLAlchemy 2.x ORM      │
                           └─────────────┬─────────────┘
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │   SQLite Database Engine  │
                           └───────────────────────────┘
```

---

## 2. Authentication & Authorization Model

### Roles & Responsibilities

| Role | Permissions |
| :--- | :--- |
| **`employee`** | - Create new document drafts.<br>- Edit and delete their own draft documents.<br>- Formally submit drafts or rejected documents for review.<br>- Trigger processing jobs on their own accessible documents.<br>- View audit events affecting their documents. |
| **`reviewer`** | - All employee capabilities.<br>- Access the global Review Queue (`/reviews`).<br>- Inspect all submitted and finalized documents across all departments.<br>- Issue binding **Approved** or **Rejected** decisions with mandatory reviewer comments.<br>- View review-related audit events. |
| **`admin`** | - Superuser privileges.<br>- Access the Administration Center (`/admin`).<br>- Provision, activate, deactivate user accounts.<br>- Change role assignments (promote employee to reviewer or admin).<br>- View complete, unfiltered platform audit logs.<br>- Access challenge mode proof telemetry in evaluation environments. |

### Access Control Rules

1. **Document Draft Privacy:** Unsubmitted draft documents are strictly private to the creating employee (and system administrators). Other employees and reviewers cannot access or list unowned drafts.
2. **Server-Side Enforcement:** Every state-changing route executes explicit ownership and role checks via decorators (`@roles_required`) and helper functions (`verify_document_access`). Hiding a UI button does not substitute for server authorization.
3. **Password Security:** All passwords are mathematically transformed using PBKDF2 with SHA-256 (or Scrypt) with unique salt per user via `werkzeug.security`. Plaintext passwords never touch logs, database columns, or error templates.
4. **Account Enumeration Defense:** Login failure produces generic error messaging (`"Invalid username or password"`) to prevent timing and enumeration attacks.

---

## 3. Document Approval State Machine

The document approval workflow implements a finite state machine:

```text
              ┌─────────┐
              │  Draft  │ ◄──────────────────────┐
              └────┬────┘                        │
                   │                             │
                   │ Submit (by Owner)           │ Edit & Resubmit
                   ▼                             │ (by Owner)
           ┌───────────────┐                     │
           │ Pending Review│                     │
           └───────┬───────┘                     │
                   │                             │
        ┌──────────┴──────────┐                  │
        │ Decide (by Reviewer)│                  │
        ▼                     ▼                  │
 ┌─────────────┐       ┌──────────────┐          │
 │  Approved   │       │   Rejected   ├──────────┘
 └─────────────┘       └──────────────┘
```

- **Draft:** Mutable by owner. Can be edited, deleted, or submitted.
- **Pending Review:** Immutable. Locked against further editing. Visible in the reviewer queue.
- **Approved:** Finalized. Permanent approval record attached. Cannot be modified or rejected.
- **Rejected:** Document requires revisions. Reviewer comments provide justification. Owner can edit content and resubmit to `pending_review`.

---

## 4. Local Document Processing Engine

The processing subsystem (`app/processing/processor.py`) implements deterministic, real local operations without external network dependencies:

1. **Document Metrics & Readability:**
   - Word count, total character count, non-space character count.
   - Sentence count and paragraph structure.
   - Automated Readability Index (ARI):
     $$\text{ARI} = 4.71 \times \left(\frac{\text{characters}}{\text{words}}\right) + 0.5 \times \left(\frac{\text{words}}{\text{sentences}}\right) - 21.43$$
   - Estimated reading time based on a standard 200 words-per-minute average.

2. **Cryptographic Checksums:**
   - Computes SHA-256, SHA-1, and MD5 hashes of the UTF-8 encoded document content.
   - Verifies payload size in bytes.

3. **Compliance & PII Detection:**
   - Scans for organizational classification markers (`CONFIDENTIAL`, `RESTRICTED`, `INTERNAL ONLY`, `PUBLIC`).
   - Scans regular expressions for simulated Social Security Numbers (`\d{3}-\d{2}-\d{4}`), Payment Cards (`(?:\d{4}-){3}\d{4}`), and email addresses.
   - Evaluates overall compliance rating (`Compliant`, `Action Required`, `Neutral`).

4. **Sanitization Preview:**
   - Generates masked representations replacing flagged PII with `[REDACTED_SSN]`, `[REDACTED_CARD]`, and `[REDACTED_EMAIL]` tags.

---

## 5. Audit Logging Architecture

Every security-relevant action triggers a persistent `AuditEvent` record:
- Authentication events (`auth.login_success`, `auth.login_failure`, `auth.logout`, `auth.dev_register`)
- Document events (`doc.create`, `doc.update`, `doc.submit`, `doc.delete`)
- Review events (`review.approve`, `review.reject`)
- Job events (`job.create`, `job.complete`)
- Admin events (`admin.user_update`)

All audit records capture:
- `actor_id` (foreign key to `User`, nullable for anonymous attempts)
- `event_type` (standardized dot-separated namespace)
- `object_type` and `object_id` (polymorphic reference to affected entity)
- `metadata_json` (structured JSON string with non-sensitive contextual details and client IP)
- `created_at` (UTC timestamp)
