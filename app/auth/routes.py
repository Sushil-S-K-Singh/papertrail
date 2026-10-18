from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from app.auth import auth_bp
from app.extensions import db
from app.models import User
from app.utils import log_audit_event


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("auth/login.html", username=username)

        user = User.query.filter_by(username=username).first()

        # Constant-time check or safe rejection without account enumeration
        if not user or not user.check_password(password):
            log_audit_event(
                event_type="auth.login_failure",
                actor=None,
                object_type="user",
                object_id=None,
                metadata={"attempted_username": username, "reason": "invalid_credentials"},
            )
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", username=username)

        if not user.active:
            log_audit_event(
                event_type="auth.login_failure",
                actor=user,
                object_type="user",
                object_id=user.id,
                metadata={"reason": "account_disabled"},
            )
            flash("Your account has been deactivated. Please contact an administrator.", "warning")
            return render_template("auth/login.html", username=username)

        # Successful authentication
        login_user(user, remember=remember)
        log_audit_event(
            event_type="auth.login_success",
            actor=user,
            object_type="user",
            object_id=user.id,
            metadata={"role": user.role},
        )
        flash(f"Welcome back, {user.username}!", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("//"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    user = current_user._get_current_object()
    log_audit_event(
        event_type="auth.logout",
        actor=user,
        object_type="user",
        object_id=user.id,
    )
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dev-register", methods=["GET", "POST"])
def dev_register():
    """Development-only registration for test accounts."""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        role = (request.form.get("role") or "employee").strip().lower()

        if role not in ("employee", "reviewer"):
            flash("Only employee or reviewer accounts may be registered via this interface.", "danger")
            return render_template("auth/dev_register.html", username=username, role=role)

        if len(username) < 3 or len(username) > 32:
            flash("Username must be between 3 and 32 characters.", "danger")
            return render_template("auth/dev_register.html", username=username, role=role)

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("auth/dev_register.html", username=username, role=role)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/dev_register.html", username=username, role=role)

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already exists. Please pick a different one.", "danger")
            return render_template("auth/dev_register.html", username=username, role=role)

        new_user = User(username=username, role=role, active=True)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        log_audit_event(
            event_type="auth.dev_register",
            actor=new_user,
            object_type="user",
            object_id=new_user.id,
            metadata={"role": new_user.role},
        )

        flash("Test account created successfully! You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/dev_register.html")
