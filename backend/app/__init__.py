"""MentorConnect Flask application factory.

``create_app()`` builds a fresh app: loads config, connects the database, enables
CORS for the Vue dev server, registers every blueprint (one per component) and the
JSON error handlers, and adds the ``flask`` CLI commands (init-db, seed-demo, run-jobs).
"""

import logging

import click
from flask import Flask
from flask_cors import CORS

from app.config import BASE_DIR, Config
from app.errors import register_error_handlers
from app.extensions import db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"))
    app.config.from_object(config_class)
    app.json.sort_keys = False
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    (BASE_DIR / "instance").mkdir(exist_ok=True)
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    register_error_handlers(app)

    from app.routes import auth, mentors, misc, profile, requests, tags
    for module in (auth, profile, tags, mentors, requests, misc):
        app.register_blueprint(module.bp)

    with app.app_context():
        from app import models  # noqa: F401 - registers every table
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            _enable_sqlite_foreign_keys()
        db.create_all()  # creates missing tables only; never drops or alters existing data
        if app.config["AUTO_SEED"]:
            from app.seed import seed_if_empty
            seed_if_empty()

    _register_cli(app)
    return app


def _enable_sqlite_foreign_keys():
    from sqlalchemy import event

    @event.listens_for(db.engine, "connect")
    def _fk_on(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")  # wait for a write lock instead of failing at once
        cursor.close()


def _register_cli(app: Flask):
    @app.cli.command("init-db")
    def init_db():
        """Create any missing tables (safe: existing data is kept)."""
        db.create_all()
        click.echo("Database tables are ready.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Insert the demo data if the database is empty."""
        from app.seed import seed_if_empty
        click.echo("Demo data inserted." if seed_if_empty() else "Database already has users; nothing changed.")

    @app.cli.command("reset-db")
    @click.option("--yes", is_flag=True, help="Confirm that ALL data should be deleted.")
    def reset_db(yes):
        """Delete ALL data and recreate the demo database. Requires --yes."""
        if not yes:
            click.echo("Refusing to delete data without --yes.")
            return
        db.drop_all()
        db.create_all()
        from app.seed import seed_if_empty
        seed_if_empty()
        click.echo("Database reset and demo data inserted.")

    @app.cli.command("run-jobs")
    def run_jobs():
        """Run the scheduled jobs once (request expiry, mentorship auto-end)."""
        from app.services.jobs import run_all
        click.echo(run_all())
