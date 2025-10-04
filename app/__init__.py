"""
__init__.py — Flask app factory.
Creates the Flask application, registers blueprints, and
initializes the database if not already set up.
"""

from flask import Flask
from app.database import initialize_database


def create_app(test_config=None):
    """Factory pattern for Flask app instance."""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key",
        DATABASE="roster.db"
    )

    # Apply test configuration if provided
    if test_config:
        app.config.update(test_config)

    # Initialize the database
    initialize_database()

    # Import routes (only after app exists)
    from app import routes
    app.register_blueprint(routes.bp)

    return app
