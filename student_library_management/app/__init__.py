import logging
import os
import click
from flask import Flask, render_template, request
from sqlalchemy.exc import OperationalError
from config import get_config
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Define it in your .env file or environment.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Define it in your .env file or environment.")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app import models  # noqa: F401  (register models for migrations)

    register_blueprints(app)
    register_error_handlers(app)
    register_security_headers(app)
    register_template_helpers(app)
    register_cli(app)

    logging.basicConfig(level=logging.INFO)
    return app


def register_blueprints(app):
    # Blueprints are registered here as each route module is added.
    from importlib import import_module
    for module, attr in ROUTE_MODULES:
        bp = getattr(import_module(module), attr)
        app.register_blueprint(bp)


# (module path, blueprint attribute) – extended as modules are implemented.
ROUTE_MODULES = [
    ("app.routes.auth", "bp"),
    ("app.routes.books", "bp"),
    ("app.routes.student", "bp"),
    ("app.routes.librarian", "bp"),
    ("app.routes.admin", "bp"),
    ("app.routes.reports", "bp"),
    ("app.routes.notifications", "bp"),
]


def register_security_headers(app):
    @app.after_request
    def set_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data:; frame-ancestors 'none'; form-action 'self'",
        )
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.endpoint != "static":
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


def register_error_handlers(app):
    def render_error(code, title, message):
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(_):
        return render_error(400, "Bad request", "The request could not be understood.")

    @app.errorhandler(403)
    def forbidden(_):
        return render_error(403, "Access denied", "You do not have permission to view this page.")

    @app.errorhandler(404)
    def not_found(_):
        return render_error(404, "Page not found", "The page or record you requested does not exist.")

    @app.errorhandler(413)
    def too_large(_):
        return render_error(413, "File too large", "The uploaded file exceeds the allowed size.")

    @app.errorhandler(OperationalError)
    def db_down(exc):
        app.logger.error("Database error: %s", exc)
        db.session.rollback()
        return render_error(503, "Service unavailable",
                            "The database is temporarily unreachable. Please try again shortly.")

    @app.errorhandler(500)
    def server_error(exc):
        app.logger.exception("Unhandled error: %s", exc)
        db.session.rollback()
        return render_error(500, "Something went wrong",
                            "An unexpected error occurred. It has been logged.")


def register_template_helpers(app):
    from app.utils.helpers import money, fmt_dt, cover_url

    app.jinja_env.filters["money"] = money
    app.jinja_env.filters["dt"] = fmt_dt
    app.jinja_env.globals["cover_url"] = cover_url

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import LibrarySetting, Notification
        ctx = {"library_name": "Student Library", "unread_count": 0}
        try:
            ctx["library_name"] = LibrarySetting.get("library_name")
            if current_user.is_authenticated:
                ctx["unread_count"] = Notification.query.filter_by(
                    user_id=current_user.id, is_read=False).count()
        except Exception:  # DB not initialised yet (e.g. during first setup)
            db.session.rollback()
        return ctx


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables (dev convenience) and seed default settings.
        For production use `flask db upgrade` instead."""
        from app.models import LibrarySetting
        db.create_all()
        LibrarySetting.seed_defaults()
        click.echo("Database tables created and default settings seeded.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Full name")
    @click.option("--email", prompt="Email")
    @click.password_option(confirmation_prompt=True)
    def create_admin(name, email, password):
        """Securely create the first (or an additional) administrator."""
        from app.models import User
        from app.utils.validators import normalize_email, validate_password
        try:
            email = normalize_email(email)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        problems = validate_password(password)
        if problems:
            raise click.ClickException(" ".join(problems))
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user with that email already exists.")
        user = User(full_name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator {email} created.")

    @app.cli.command("seed-demo")
    @click.option("--password", prompt="Password to assign to demo accounts", hide_input=True,
                  confirmation_prompt=True)
    def seed_demo(password):
        """Insert OPTIONAL demo data (categories, books, copies, 1 librarian, 3 students)."""
        from app.services.demo_data import seed
        problems = __import__("app.utils.validators", fromlist=["x"]).validate_password(password)
        if problems:
            raise click.ClickException(" ".join(problems))
        click.echo(seed(password))
