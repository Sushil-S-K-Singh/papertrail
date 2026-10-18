import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, redirect, render_template, url_for
from config import config_by_name
from app.extensions import csrf, db, login_manager


def create_app(config_name: str = None) -> Flask:
    """Application factory for PaperTrail Document Portal."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    cfg_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg_class)

    # Ensure instance directory exists
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.documents import documents_bp
    from app.reviews import reviews_bp
    from app.processing import processing_bp
    from app.admin import admin_bp
    from app.audit import audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(processing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(audit_bp)

    # Convenience alias for /review -> /reviews
    @app.route("/review")
    def review_alias():
        return redirect(url_for("reviews.review_queue"))

    # Register custom error handlers
    register_error_handlers(app)

    # Global context processors for templates
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "app_name": "PaperTrail",
            "app_tagline": "Enterprise Document Approval & Audit Tracking",
        }

    return app


def register_error_handlers(app: Flask):
    """Register custom error pages for 403, 404, and 500 HTTP errors."""
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500
