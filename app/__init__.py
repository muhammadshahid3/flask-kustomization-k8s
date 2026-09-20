import hmac
import secrets
from decimal import Decimal

from flask import Flask, abort, render_template, request, session
from flask_login import current_user
from markupsafe import Markup
from sqlalchemy import func

from config import Config

from .extensions import db, login_manager, migrate


def money(value):
    """Jinja filter: 12.5 -> $12.50"""
    return f"${Decimal(value):,.2f}"


def csrf_input():
    """Jinja helper: returns a hidden CSRF input for every POST form."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "DATABASE_URL is not set. Example: "
            "postgresql://postgres:change_me@db:5432/stockflow"
        )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"

    # Import models so Flask-Migrate can see them
    from .models import CartItem

    # Blueprints
    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .cart import bp as cart_bp
    from .orders import bp as orders_bp
    from .products import bp as products_bp

    app.register_blueprint(products_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    # CLI commands: flask seed / flask create-admin
    from .seed import create_admin_command, seed_command

    app.cli.add_command(seed_command)
    app.cli.add_command(create_admin_command)

    app.add_template_filter(money, "money")

    @app.before_request
    def csrf_protect():
        # Every POST form must contain the hidden token added by csrf_input()
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token", "")
            expected = session.get("_csrf_token", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(
                    400,
                    description="Your session expired or the form was invalid. "
                    "Please go back, refresh the page and try again.",
                )

    @app.context_processor
    def inject_template_globals():
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = (
                db.session.query(func.coalesce(func.sum(CartItem.quantity), 0))
                .filter(CartItem.user_id == current_user.id)
                .scalar()
            )
        return {"cart_count": int(cart_count), "csrf_input": csrf_input}

    def render_error(error):
        return render_template("error.html", error=error), error.code

    for code in (400, 403, 404):
        app.register_error_handler(code, render_error)

    return app
