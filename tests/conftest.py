import pytest
from app import create_app
from app.extensions import db
from app.models import Document, User


@pytest.fixture
def app():
    """Creates an application instance configured for testing."""
    test_app = create_app("testing")

    with test_app.app_context():
        db.create_all()

        # Create standardized test users
        admin = User(username="admin_user", role="admin", active=True)
        admin.set_password("AdminPass123!")
        db.session.add(admin)

        reviewer = User(username="reviewer_user", role="reviewer", active=True)
        reviewer.set_password("ReviewerPass123!")
        db.session.add(reviewer)

        emp1 = User(username="emp_alice", role="employee", active=True)
        emp1.set_password("EmployeePass123!")
        db.session.add(emp1)

        emp2 = User(username="emp_bob", role="employee", active=True)
        emp2.set_password("EmployeePass123!")
        db.session.add(emp2)

        disabled = User(username="disabled_user", role="employee", active=False)
        disabled.set_password("EmployeePass123!")
        db.session.add(disabled)

        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username="emp_alice", password="EmployeePass123!"):
        return self._client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def logout(self):
        return self._client.post("/logout", follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)
