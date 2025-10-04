"""
conftest.py — Shared fixtures for pytest.
"""

import os
import tempfile
import pytest
from app import create_app
from app.database import create_tables


@pytest.fixture
def app():
    """Provide a Flask app configured for testing."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({"TESTING": True, "DATABASE": db_path})
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Return a test client for the Flask app."""
    return app.test_client()
