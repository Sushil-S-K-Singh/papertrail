from flask import Blueprint

processing_bp = Blueprint("processing", __name__, url_prefix="/jobs")

from app.processing import routes  # noqa: E402, F401
