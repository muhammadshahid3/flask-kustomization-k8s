from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import CartItem, Product

bp = Blueprint("cart", __name__)


def redirect_back(default_endpoint, **values):
    """Go back to the page the user came from (same site only)."""
    referrer = request.referrer
    if referrer and urlparse(referrer).netloc == request.host:
        return redirect(referrer)
    return redirect(url_for(default_endpoint, **values))


def get_own_item_or_404(item_id):
    item = db.get_or_404(CartItem, item_id)
    if item.user_id != current_user.id:
        abort(404)
    return item


@bp.route("/cart")
@login_required
def view_cart():
    return render_template(
        "cart.html", items=current_user.cart_items, total=current_user.cart_total
    )


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = db.get_or_404(Product, product_id)

    # Visitors who are not logged in are sent to the login page (with a signup link)
    if not current_user.is_authenticated:
        flash("Please log in or sign up to add items to your cart.", "info")
        return redirect(
            url_for("auth.login", next=url_for("products.product_detail", product_id=product.id))
        )

    quantity = request.form.get("quantity", 1, type=int)
    if quantity < 1:
        quantity = 1

    if product.stock_quantity < 1:
        flash(f"Sorry, {product.name} is out of stock.", "warning")
        return redirect_back("products.product_list")

    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    new_quantity = (item.quantity if item else 0) + quantity

    if new_quantity > product.stock_quantity:
        new_quantity = product.stock_quantity
        flash(
            f"Only {product.stock_quantity} of {product.name} in stock. "
            "Your cart has been set to the maximum available.",
            "warning",
        )
    else:
        flash(f"Added {product.name} to your cart.", "success")

    if item:
        item.quantity = new_quantity
    else:
        db.session.add(
            CartItem(user_id=current_user.id, product_id=product.id, quantity=new_quantity)
        )

    try:
        db.session.commit()
    except IntegrityError:  # e.g. double click created the same row twice
        db.session.rollback()
        flash("Could not update your cart. Please try again.", "danger")

    return redirect_back("products.product_list")


@bp.route("/cart/increase/<int:item_id>", methods=["POST"])
@login_required
def increase(item_id):
    item = get_own_item_or_404(item_id)
    if item.quantity + 1 > item.product.stock_quantity:
        flash(f"Only {item.product.stock_quantity} of {item.product.name} in stock.", "warning")
    else:
        item.quantity += 1
        db.session.commit()
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/decrease/<int:item_id>", methods=["POST"])
@login_required
def decrease(item_id):
    item = get_own_item_or_404(item_id)
    if item.quantity <= 1:
        db.session.delete(item)
    else:
        item.quantity -= 1
    db.session.commit()
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove(item_id):
    item = get_own_item_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from your cart.", "info")
    return redirect(url_for("cart.view_cart"))
