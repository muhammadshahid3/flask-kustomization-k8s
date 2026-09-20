from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from .extensions import db
from .models import Category, Order, Product, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def require_admin():
    """Runs before EVERY admin route: only logged-in admins get through."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.admin_login", next=request.path))
    if not current_user.is_admin:
        abort(403)


# ---------------------------------------------------------------- Dashboard
@bp.route("/")
def dashboard():
    stats = {
        "products": Product.query.count(),
        "categories": Category.query.count(),
        "customers": User.query.filter_by(is_admin=False).count(),
        "orders": Order.query.count(),
    }
    low_stock = (
        Product.query.filter(Product.stock_quantity <= 5)
        .order_by(Product.stock_quantity, Product.name)
        .limit(5)
        .all()
    )
    return render_template("admin/dashboard.html", stats=stats, low_stock=low_stock)


# --------------------------------------------------------------- Categories
@bp.route("/categories")
def categories():
    items = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=items)


def category_name_error(name, exclude_id=None):
    if not name:
        return "Category name is required."
    if len(name) > 100:
        return "Category name is too long (100 characters max)."
    query = Category.query.filter(func.lower(Category.name) == name.lower())
    if exclude_id:
        query = query.filter(Category.id != exclude_id)
    if query.first():
        return "A category with this name already exists."
    return None


@bp.route("/categories/add", methods=["POST"])
def add_category():
    name = request.form.get("name", "").strip()
    error = category_name_error(name)
    if error:
        flash(error, "danger")
    else:
        db.session.add(Category(name=name))
        db.session.commit()
        flash(f"Category '{name}' added.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/edit", methods=["POST"])
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    name = request.form.get("name", "").strip()
    error = category_name_error(name, exclude_id=category.id)
    if error:
        flash(error, "danger")
    else:
        category.name = name
        db.session.commit()
        flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    product_count = len(category.products)
    db.session.delete(category)  # its products just become "Uncategorized"
    db.session.commit()
    message = f"Category '{category.name}' deleted."
    if product_count:
        message += f" {product_count} product(s) are now uncategorized."
    flash(message, "info")
    return redirect(url_for("admin.categories"))


# ----------------------------------------------------------------- Products
@bp.route("/products")
def products():
    items = Product.query.order_by(Product.name).all()
    return render_template("admin/products.html", products=items)


def parse_product_form(form):
    """Validate the product form. Returns (cleaned_values, list_of_errors)."""
    errors = []
    values = {
        "name": form.get("name", "").strip(),
        "description": form.get("description", "").strip(),
        "image_url": form.get("image_url", "").strip(),
        "price": None,
        "stock_quantity": None,
        "category_id": None,
    }

    if not values["name"]:
        errors.append("Product name is required.")
    elif len(values["name"]) > 200:
        errors.append("Product name is too long (200 characters max).")

    try:
        price = Decimal(form.get("price", "").strip())
        if not price.is_finite() or price < 0 or price >= Decimal("100000000"):
            raise InvalidOperation
        values["price"] = price.quantize(Decimal("0.01"))
    except InvalidOperation:
        errors.append("Price must be a number between 0 and 99,999,999.99.")

    try:
        stock = int(form.get("stock_quantity", "").strip())
        if stock < 0 or stock > 1000000:
            raise ValueError
        values["stock_quantity"] = stock
    except ValueError:
        errors.append("Stock quantity must be a whole number (0 or more).")

    image_url = values["image_url"]
    if image_url:
        if len(image_url) > 500:
            errors.append("Image URL is too long (500 characters max).")
        elif not image_url.startswith(("http://", "https://", "/")):
            errors.append("Image URL must start with http://, https:// or /")

    category_raw = form.get("category_id", "").strip()
    if category_raw:
        try:
            category = db.session.get(Category, int(category_raw))
        except ValueError:
            category = None
        if category is None:
            errors.append("Please choose a valid category.")
        else:
            values["category_id"] = category.id

    return values, errors


def product_to_form_values(product):
    return {
        "name": product.name,
        "description": product.description or "",
        "price": str(product.price),
        "stock_quantity": str(product.stock_quantity),
        "image_url": product.image_url or "",
        "category_id": str(product.category_id or ""),
    }


def render_product_form(title, action, values):
    return render_template(
        "admin/product_form.html",
        title=title,
        action=action,
        values=values,
        categories=Category.query.order_by(Category.name).all(),
    )


@bp.route("/products/add", methods=["GET", "POST"])
def add_product():
    action = url_for("admin.add_product")
    if request.method == "POST":
        values, errors = parse_product_form(request.form)
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_product_form("Add Product", action, request.form)
        product = Product(
            name=values["name"],
            description=values["description"] or None,
            price=values["price"],
            stock_quantity=values["stock_quantity"],
            image_url=values["image_url"] or None,
            category_id=values["category_id"],
        )
        db.session.add(product)
        db.session.commit()
        flash(f"Product '{product.name}' added.", "success")
        return redirect(url_for("admin.products"))
    return render_product_form("Add Product", action, {})


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    action = url_for("admin.edit_product", product_id=product.id)
    if request.method == "POST":
        values, errors = parse_product_form(request.form)
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_product_form("Edit Product", action, request.form)
        product.name = values["name"]
        product.description = values["description"] or None
        product.price = values["price"]
        product.stock_quantity = values["stock_quantity"]
        product.image_url = values["image_url"] or None
        product.category_id = values["category_id"]
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))
    return render_product_form("Edit Product", action, product_to_form_values(product))


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    name = product.name
    db.session.delete(product)  # removes it from carts; old orders keep their history
    db.session.commit()
    flash(f"Product '{name}' deleted.", "info")
    return redirect(url_for("admin.products"))
