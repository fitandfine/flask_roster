"""
routes.py — Example Flask routes for the Roster App.
"""

from flask import Blueprint, jsonify
import sqlite3

bp = Blueprint("routes", __name__)

@bp.route("/")
def index():
    """Return a simple health-check or welcome message."""
    return jsonify({"message": "Roster App is running!"})
