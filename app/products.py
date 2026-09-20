from flask import Blueprint, render_template, request

from .extensions import db
from .models import Category, Product

bp = Blueprint("products", __name__)


def like_pattern(text):
    """Escape % and _ so users can search for them literally."""
    text = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{text}%"


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/products")
def product_list():
    q = request.args.get("q", "").strip()
    selected_category = request.args.get("category", type=int)

    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(like_pattern(q), escape="\\"))
    if selected_category:
        query = query.filter(Product.category_id == selected_category)

    products = query.order_by(Product.name).all()
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "products.html",
        products=products,
        categories=categories,
        q=q,
        selected_category=selected_category,
    )


@bp.route("/products/<int:product_id>")
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    return render_template("product_detail.html", product=product)
