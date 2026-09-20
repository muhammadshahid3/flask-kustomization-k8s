from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import User

bp = Blueprint("auth", __name__)


def safe_next_url(target):
    """Only allow redirects to paths on this site (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("products.product_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(name) > 100:
            error = "Name is too long (100 characters max)."
        elif "@" not in email or len(email) > 255:
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters long."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."

        if error:
            flash(error, "danger")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("An account with this email already exists.", "danger")
                return render_template("signup.html")
            login_user(user)
            flash(f"Welcome to StockFlow, {user.name}!", "success")
            return redirect(
                safe_next_url(request.args.get("next")) or url_for("products.product_list")
            )

    return render_template("signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("products.product_list"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("You are now logged in.", "success")
            return redirect(
                safe_next_url(request.args.get("next")) or url_for("products.product_list")
            )
        flash("Invalid email or password.", "danger")

    return render_template("login.html", admin_login=False)


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        # Same message for "wrong password" and "not an admin"
        if user and user.is_admin and user.check_password(password):
            login_user(user)
            flash("Welcome back, admin.", "success")
            return redirect(
                safe_next_url(request.args.get("next")) or url_for("admin.dashboard")
            )
        flash("Invalid admin credentials.", "danger")

    return render_template("login.html", admin_login=True)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("products.index"))
