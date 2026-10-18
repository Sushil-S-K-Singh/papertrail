# PaperTrail — Enterprise Document Approval and Tracking Portal

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/pytest-48%20passed-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Ubuntu%2024.04%20LTS%20%7C%20Windows-lightgrey.svg)]()

**PaperTrail** is a production-grade, enterprise-oriented document approval, processing, and audit tracking platform built with Python Flask, SQLAlchemy, SQLite, Jinja2, and Vanilla JavaScript.

The platform provides a secure internal portal where employees can draft and submit documents, qualified reviewers inspect and decide on submissions, local background workers execute deterministic processing tasks (SHA-256 integrity verification, compliance scanning, readability metrics, redaction), and system administrators monitor platform telemetry and governance audit trails.

---

## Key Features

- **Session-Based Authentication & Role Scoping:**
  - Secure session handling via `Flask-Login`.
  - Password hashing via `Werkzeug` PBKDF2/Scrypt algorithms.
  - Three distinct roles: `employee`, `reviewer`, and `admin`.
  - Safe error messages that prevent user enumeration leaks.
  - Development account registration interface (`/dev-register`) for quick persona testing.

- **Document Governance & Approval State Machine:**
  - Strict workflow state transitions: `draft` &rarr; `pending_review` &rarr; `approved` / `rejected`.
  - Granular ownership controls: employees can only view, edit, or delete their own drafts.
  - Reviewers and administrators review submissions with mandatory decision records and justification comments.
  - Resubmission workflow for rejected proposals after revisions.

- **Bounded Local Processing Jobs:**
  - Real, bounded local document processing engine with persistent state in SQLite:
    - **Document Analysis:** Computes word counts, character counts, sentence structures, average word lengths, estimated reading time, and Automated Readability Index (ARI) grade levels.
    - **Cryptographic Integrity Check:** Calculates SHA-256, SHA-1, and MD5 hashes of document content with byte payload verification.
    - **Regulatory & Compliance Scan:** Scans for classification labels (`CONFIDENTIAL`, `RESTRICTED`, `INTERNAL ONLY`) and flags simulated PII patterns (SSNs, credit card formats, corporate emails).
    - **Data Sanitization & Redaction:** Generates sanitized previews masking identifiable data with `[REDACTED]` tokens.

- **Immutable Audit Trail:**
  - Centralized audit logging of authentication successes/failures, document state changes, managerial approvals/rejections, processing job dispatches, and administrator updates.
  - Strict exclusion of sensitive data (no passwords, session tokens, or secrets logged).
  - Searchable and filterable by event type and target object type.

- **System Administration & Telemetry:**
  - Protected admin console (`/admin`) displaying active accounts, role configurations, platform statistics, and system-wide audit feeds.
  - User management: toggle account active status and promote/demote user roles.
  - Optional Challenge Mode indicator for evaluation environments with administrative proof tokens.

- **Zero External Frontend Dependencies:**
  - Rendered entirely offline with native HTML5, modern CSS3 (Flexbox & Grid), and Vanilla JavaScript.
  - Responsive layouts, system font stacks, and accessible interactive controls (password visibility toggles, dismissible alerts, confirmation prompts).

---

## Project Structure

```text
papertrail/
├── run.py                       # Application entry point (localhost binding, debug off)
├── requirements.txt             # Pinned Python package dependencies
├── config.py                    # Environment-aware configuration (Dev, Test, Prod)
├── README.md                    # System documentation and execution guide
├── .gitignore                   # Version control ignore rules
├── app/
│   ├── __init__.py              # Application factory (create_app) & error handlers
│   ├── extensions.py            # SQLAlchemy, LoginManager, and CSRF instances
│   ├── models.py                # Database models (User, Document, Approval, Job, Audit)
│   ├── utils.py                 # Authorization decorators & audit logging helpers
│   ├── auth/                    # Authentication blueprint (/login, /logout, /dev-register)
│   ├── dashboard/               # Landing page, role dashboards, and /health
│   ├── documents/               # Document CRUD, search, filter, and state transitions
│   ├── reviews/                 # Review queue and approval/rejection endpoints
│   ├── processing/              # Processing jobs dashboard & execution engine
│   ├── admin/                   # Administrator governance & user management
│   ├── audit/                   # Audit log browser with event filtering
│   ├── templates/               # Jinja2 server-rendered templates
│   │   ├── base.html            # Master layout with responsive navigation
│   │   ├── landing.html         # Public marketing homepage
│   │   ├── auth/                # Login and test account registration
│   │   ├── dashboard/           # Main role-specific dashboard
│   │   ├── documents/           # List, new, detail, and edit templates
│   │   ├── reviews/             # Review queue and decision history
│   │   ├── processing/          # Jobs dashboard and structured payload detail
│   │   ├── admin/               # Administration center
│   │   ├── audit/               # Audit trail browser
│   │   └── errors/              # Custom 403, 404, 500 error pages
│   └── static/
│       ├── css/                 # main.css, components.css, dashboard.css
│       └── js/                  # main.js, dashboard.js
├── scripts/
│   ├── __init__.py
│   ├── init_db.py               # Schema initialization script
│   └── seed_db.py               # Deterministic synthetic seed data loader
├── deployment/
│   ├── setup.sh                 # Production deployment script for Ubuntu 24.04 LTS
│   ├── healthcheck.sh           # Systemd and HTTP health probe
│   ├── reset.sh                 # Safe database reset to clean baseline
│   └── papertrail.service       # Systemd unit running Gunicorn WSGI
├── tests/                       # Complete pytest integration test suite (48 tests)
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_dashboard.py
│   ├── test_documents.py
│   ├── test_reviews.py
│   ├── test_processing.py
│   ├── test_admin.py
│   ├── test_authorization.py
│   └── test_health_and_errors.py
└── docs/
    └── architecture.md          # Technical architecture & security specification
```

---

## Local Quickstart & Run Instructions

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- `pip` and `venv`

### 2. Environment Setup

```bash
# Clone or navigate into the project directory
cd papertrail

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Initialize & Seed Database

```bash
# Initialize SQLite database schema
python -m scripts.init_db

# Load deterministic synthetic seed data
python -m scripts.seed_db
```

### 4. Run the Development Server

```bash
python run.py
```

The application will bind to `http://127.0.0.1:5000` with debug mode disabled by default.

---

## Pre-Seeded Development Accounts

For testing, review, and demonstration, the following synthetic accounts are pre-seeded deterministically:

| Username | Password | Role | Permissions & Responsibilities |
| :--- | :--- | :--- | :--- |
| `alice_emp` | `EmployeePass123!` | `employee` | Draft proposals, submit for review, view own documents |
| `bob_emp` | `EmployeePass123!` | `employee` | Draft proposals, submit for review |
| `carol_emp` | `EmployeePass123!` | `employee` | Draft proposals, submit for review |
| `rachel_rev` | `ReviewerPass123!` | `reviewer` | Inspect review queue, approve/reject submissions with comments |
| `victor_rev` | `ReviewerPass123!` | `reviewer` | Inspect review queue, approve/reject submissions with comments |
| `admin` | `AdminSecure2026!` | `admin` | Full system access, user role modification, system audit log |

*Note: New test employee or reviewer accounts can also be created dynamically via the `/dev-register` route.*

---

## Implemented Pages & Endpoints

| URL Route | Methods | Role Required | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Marketing landing page with hero, dashboard preview, feature cards, and workflow overview |
| `/login` | `GET`, `POST` | Public | Enterprise login form with password visibility toggle and CSRF protection |
| `/logout` | `POST` | Authenticated | Clears user session and logs audit event |
| `/dev-register` | `GET`, `POST` | Public | Development registration for test personas (`employee`, `reviewer`) |
| `/dashboard` | `GET` | Authenticated | Role-tailored dashboard with DB-calculated statistics, pipeline distribution, and recent activity |
| `/documents` | `GET` | Authenticated | Document management interface with title search, status/category filter, and sorting |
| `/documents/new` | `GET`, `POST` | Authenticated | Create document form with draft saving and instant submission options |
| `/documents/<id>` | `GET` | Scoped Access | Document detail page with metadata, content, approval history, audit trail, and contextual actions |
| `/documents/<id>/edit` | `GET`, `POST` | Owner / Admin | Modify draft or rejected document content and title |
| `/documents/<id>/submit` | `POST` | Owner / Admin | Formal submission transition (`draft` &rarr; `pending_review`) |
| `/documents/<id>/delete` | `POST` | Owner / Admin | Delete draft document |
| `/review` / `/reviews` | `GET` | Reviewer, Admin | Review queue displaying pending submissions and past decision log |
| `/reviews/<id>/decide` | `POST` | Reviewer, Admin | Submit binding approval or rejection with justification comment |
| `/jobs` | `GET` | Authenticated | Document processing dashboard and job dispatcher |
| `/jobs/new` | `POST` | Authenticated | Trigger background analysis, cryptographic hash check, compliance scan, or redaction |
| `/jobs/<id>` | `GET` | Scoped Access | Detailed job execution log and formatted JSON payload results |
| `/admin` | `GET` | Administrator | System governance console with telemetry, user management, and challenge proof indicator |
| `/admin/users/<id>/toggle-active` | `POST` | Administrator | Activate or deactivate user accounts |
| `/admin/users/<id>/change-role` | `POST` | Administrator | Update user permissions between employee, reviewer, and admin |
| `/audit` | `GET` | Authenticated | Audit log viewer with event type and object type filters |
| `/health` | `GET` | Public | Healthcheck endpoint returning JSON `{"status": "ok", "database": "connected"}` |

---

## Production Deployment (Ubuntu Server 24.04 LTS)

PaperTrail includes automated scripts for deployment, health verification, and reset on Ubuntu Server 24.04:

```bash
# 1. Run deployment script as root / sudo
sudo bash deployment/setup.sh

# 2. Run system health check
bash deployment/healthcheck.sh

# 3. Reset database to clean baseline if needed
sudo bash deployment/reset.sh
```

### Production Service Configuration
The application is served via **Gunicorn** managed by a **systemd** service:
- Unit file: `/etc/systemd/system/papertrail.service`
- Unprivileged user: `papertrail:papertrail`
- Workers: 3 sync workers listening on `127.0.0.1:5000`
- Logs: managed via `journalctl -u papertrail`

---

## Automated Testing Suite

Automated integration and unit tests are implemented using `pytest` and the Flask test client against an isolated in-memory SQLite database.

To execute the test suite:

```bash
python -m pytest -v
```

### Test Coverage Highlights (48 tests passing):
- **Authentication (`tests/test_auth.py`):** Landing page, login success/failure, deactivated accounts, password hashing, dev registration validation, logout.
- **Authorization & Ownership (`tests/test_authorization.py`):** Employee draft isolation, cross-user edit prevention, delete protections, role separation for `/admin` and `/review`.
- **Dashboards (`tests/test_dashboard.py`):** Database-backed stats calculation, role-specific scoping.
- **Documents (`tests/test_documents.py`):** CRUD operations, server validation, search, status and category filtering.
- **Review Workflow (`tests/test_reviews.py`):** Review queue, approvals, rejections, invalid workflow state transitions.
- **Processing Jobs (`tests/test_processing.py`):** Real document analysis metrics, SHA-256 calculation, PII pattern detection, sanitization masks.
- **Administration (`tests/test_admin.py`):** User activation toggling, self-deactivation prevention, role management, challenge mode indicator.
- **Health & Errors (`tests/test_health_and_errors.py`):** Health JSON probe, custom 403, 404, 500 error templates, audit filtering.

---

## License & Attribution

Internal corporate software developed for PaperTrail Enterprise. Created in compliance with secure web development standards and OWASP Web Security guidelines.
