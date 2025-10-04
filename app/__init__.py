from flask import Flask
from app.routes import bp as main_bp
from app.database import initialize_database, close_db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE="roster.db"
    )

    if test_config:
        app.config.update(test_config)

    if not app.config.get("TESTING"):
        initialize_database()

    app.register_blueprint(main_bp)
    app.teardown_appcontext(close_db)

    return app
