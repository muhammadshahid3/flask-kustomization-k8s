import re
from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Order, OrderItem, Product

bp = Blueprint("orders", __name__)

PHONE_PATTERN = re.compile(r"[0-9+()\-\s]{7,20}")


def validate_checkout(data):
    errors = []
    if not all(data.values()):
        errors.append("Please fill in all fields.")
        return errors
    if len(data["full_name"]) > 100:
        errors.append("Full name is too long.")
    if "@" not in data["email"] or len(data["email"]) > 255:
        errors.append("Please enter a valid email address.")
    if not PHONE_PATTERN.fullmatch(data["phone"]):
        errors.append("Please enter a valid phone number (7-20 digits, spaces, + - ( ) allowed).")
    if len(data["address"]) > 255:
        errors.append("Address is too long (255 characters max).")
    if len(data["city"]) > 100:
        errors.append("City is too long.")
    return errors


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = list(current_user.cart_items)
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("products.product_list"))

    form = {"full_name": current_user.name, "email": current_user.email}

    if request.method == "POST":
        fields = ("full_name", "email", "phone", "address", "city")
        form = {field: request.form.get(field, "").strip() for field in fields}
        errors = validate_checkout(form)

        if not errors:
            # Lock the product rows so two customers cannot buy the last item together
            product_ids = sorted({item.product_id for item in items})
            products = (
                Product.query.filter(Product.id.in_(product_ids))
                .order_by(Product.id)
                .populate_existing()
                .with_for_update()
                .all()
            )
            products_by_id = {product.id: product for product in products}

            for item in items:
                product = products_by_id[item.product_id]
                if item.quantity > product.stock_quantity:
                    errors.append(
                        f"Only {product.stock_quantity} of {product.name} left in stock. "
                        "Please update your cart."
                    )

            if errors:
                for message in errors:
                    flash(message, "danger")
                return redirect(url_for("cart.view_cart"))

            order = Order(
                user_id=current_user.id,
                full_name=form["full_name"],
                email=form["email"],
                phone=form["phone"],
                address=form["address"],
                city=form["city"],
                total_amount=Decimal("0.00"),
            )
            total = Decimal("0.00")
            for item in items:
                product = products_by_id[item.product_id]
                product.stock_quantity -= item.quantity
                order.items.append(
                    OrderItem(
                        product_id=product.id,
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=item.quantity,
                    )
                )
                total += product.price * item.quantity
                db.session.delete(item)
            order.total_amount = total

            db.session.add(order)
            db.session.commit()
            flash("Thank you! Your order has been placed.", "success")
            return redirect(url_for("orders.order_detail", order_id=order.id))

        for message in errors:
            flash(message, "danger")

    return render_template(
        "checkout.html", items=items, total=current_user.cart_total, form=form
    )


@bp.route("/orders")
@login_required
def my_orders():
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("orders.html", orders=orders)


@bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(404)
    return render_template("order_detail.html", order=order)
