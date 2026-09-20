import os
from decimal import Decimal

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Category, Product, User

CATEGORIES = ["Electronics", "Home & Kitchen", "Accessories"]

# (name, description, price, stock, category, image seed)
PRODUCTS = [
    ("Wireless Headphones", "Over-ear Bluetooth headphones with 30 hours of battery life.", "59.99", 25, "Electronics", "headphones"),
    ("Mechanical Keyboard", "Compact keyboard with tactile switches and white backlight.", "79.00", 15, "Electronics", "keyboard"),
    ("Bluetooth Speaker", "Portable water-resistant speaker with punchy bass.", "34.50", 40, "Electronics", "speaker"),
    ("Ceramic Mug Set", "Set of four 350 ml ceramic mugs, dishwasher safe.", "24.99", 30, "Home & Kitchen", "mugs"),
    ("Steel Water Bottle", "Insulated 750 ml bottle. Keeps drinks cold for 24 hours.", "18.00", 60, "Home & Kitchen", "bottle"),
    ("LED Desk Lamp", "Dimmable desk lamp with three colour temperatures.", "29.95", 20, "Home & Kitchen", "lamp"),
    ("Canvas Backpack", "Everyday 20 L backpack with a padded laptop sleeve.", "45.00", 12, "Accessories", "backpack"),
    ("Leather Wallet", "Slim bifold wallet with RFID protection. Limited stock!", "32.00", 2, "Accessories", "wallet"),
]


def image_for(seed):
    return f"https://picsum.photos/seed/stockflow-{seed}/600/400"


def ensure_admin(name, email, password):
    """Create the admin, or reset the password if this email is already an admin."""
    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()
    if user and not user.is_admin:
        click.echo(f"! {email} is already a normal customer account - not changed.")
        return None
    if user is None:
        user = User(name=name, email=email, is_admin=True)
        db.session.add(user)
    user.set_password(password)
    db.session.commit()
    return user


@click.command("seed")
@with_appcontext
def seed_command():
    """Add sample data. Safe to run many times (it never duplicates data)."""
    # Categories and products: only when the store is completely empty
    if Category.query.count() == 0 and Product.query.count() == 0:
        categories = {name: Category(name=name) for name in CATEGORIES}
        db.session.add_all(categories.values())
        for name, description, price, stock, category, image in PRODUCTS:
            db.session.add(
                Product(
                    name=name,
                    description=description,
                    price=Decimal(price),
                    stock_quantity=stock,
                    category=categories[category],
                    image_url=image_for(image),
                )
            )
        db.session.commit()
        click.echo(f"Seeded {len(CATEGORIES)} categories and {len(PRODUCTS)} products.")
    else:
        click.echo("Categories/products already exist - skipping sample data.")

    # Development admin: only when no admin exists yet
    if User.query.filter_by(is_admin=True).first() is None:
        name = os.environ.get("ADMIN_NAME", "Store Admin")
        email = os.environ.get("ADMIN_EMAIL", "admin@stockflow.local")
        password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
        if ensure_admin(name, email, password):
            click.echo(f"Created development admin: {email}")
            click.echo("!! CHANGE THE ADMIN EMAIL/PASSWORD BEFORE GOING TO PRODUCTION !!")
    else:
        click.echo("An admin account already exists - skipping admin creation.")


@click.command("create-admin")
@click.option("--name", default="Store Admin", show_default=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_admin_command(name, email, password):
    """Create an admin user, or reset the password of an existing admin."""
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters long.")
    user = ensure_admin(name, email, password)
    if user:
        click.echo(f"Admin ready: {user.email}")
