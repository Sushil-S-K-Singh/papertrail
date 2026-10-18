import sys
from app import create_app
from app.extensions import db


def init_db():
    """Initializes the database schema."""
    app = create_app()
    with app.app_context():
        print("[*] Creating database tables...")
        db.create_all()
        print("[+] Database schema successfully initialized.")


if __name__ == "__main__":
    init_db()
