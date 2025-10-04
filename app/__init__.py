import os
from flask import Flask
from app.routes import bp as main_bp
from app.database import initialize_database, close_db

def create_app(test_config=None):
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))  # app/
    db_path = os.path.join(base_dir, "..", "roster.db")

    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=db_path
    )

    if test_config:
        app.config.update(test_config)

    # Only initialize database when not testing
    if not app.config.get("TESTING"):
        # Must push application context before using current_app
        with app.app_context():
            initialize_database()

    app.register_blueprint(main_bp)
    app.teardown_appcontext(close_db)

    return app
