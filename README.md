# StockFlow Store

A small, beginner-friendly e-commerce app: **Flask + PostgreSQL + SQLAlchemy + Flask-Migrate + Flask-Login + Jinja2 + Bootstrap 5**, running entirely with **Docker Compose**.

```
Browser → localhost:5000 → web container (Gunicorn + Flask) → db:5432 → db container (PostgreSQL)
```

## Folder structure

```
stockflow/
├── app/
│   ├── __init__.py          # create_app(): wires extensions, blueprints, CSRF, error pages
│   ├── extensions.py        # db, migrate, login_manager (avoids circular imports)
│   ├── models.py            # User, Category, Product, CartItem, Order, OrderItem
│   ├── auth.py              # signup, login, logout, admin login
│   ├── admin.py             # admin dashboard, categories, products (admins only)
│   ├── products.py          # landing page, product list/search/filter, product detail
│   ├── cart.py              # add / increase / decrease / remove
│   ├── orders.py            # checkout, my orders, order detail
│   ├── seed.py              # `flask seed` and `flask create-admin` commands
│   ├── templates/           # Jinja2 templates (base, pages, admin/)
│   └── static/              # css/, js/, img/
├── migrations/              # Alembic/Flask-Migrate (already initialised, initial migration included)
├── config.py
├── run.py                   # `run:app` is what Gunicorn starts
├── requirements.txt
├── Dockerfile
├── docker-entrypoint.sh     # wait for DB → flask db upgrade → (optional seed) → Gunicorn
├── docker-compose.yml       # services: web, db (+ named volume postgres_data)
├── .dockerignore  .gitignore  .env.example
└── README.md
```

## Quick start

```bash
cp .env.example .env          # then edit .env (at least POSTGRES_PASSWORD and SECRET_KEY)
docker compose build
docker compose up -d
docker compose logs -f        # wait for "Starting: gunicorn ..." then press Ctrl+C
```

Open **http://localhost:5000**

On first start the entrypoint automatically applies the migrations and loads sample data
(3 categories, 8 products) plus a development admin.

### Development admin credentials

| Field    | Value                   |
|----------|-------------------------|
| Login at | http://localhost:5000/admin/login |
| Email    | `admin@stockflow.local` |
| Password | `Admin@12345`           |

> **Change these before production.** Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` *before the first start*,
> or reset the password of an existing admin later:
> `docker compose exec web flask create-admin --email admin@stockflow.local`
> (you will be prompted for a new password). Also change `SECRET_KEY` and `POSTGRES_PASSWORD`,
> and set `SEED_ON_START=false`.

Normal users sign up at `/signup`. Admin routes (`/admin/...`) return **403** for normal users and redirect visitors to the admin login.

## Docker commands

| Purpose | Command |
|---|---|
| Build | `docker compose build` |
| Start | `docker compose up -d` |
| Rebuild + start (after code changes) | `docker compose up -d --build` |
| View logs | `docker compose logs -f` (one service: `docker compose logs -f web`) |
| Status | `docker compose ps` |
| Stop | `docker compose down` |
| Stop **and delete the database volume** | `docker compose down -v` |

## Database migrations

* The `migrations/` folder is **already initialised** (`flask db init` was done) and contains the initial migration, so **do not run `flask db init` again**.
* Every time the `web` container starts, `docker-entrypoint.sh` runs `flask db upgrade`. It only *applies* the committed migration files; it never creates new ones.

Run Flask-Migrate commands inside the running container:

```bash
docker compose exec web flask db current      # which revision is applied
docker compose exec web flask db history      # list revisions
docker compose exec web flask db upgrade      # apply pending migrations manually
docker compose exec web flask db downgrade    # go back one revision
```

### Changing the models (creating a new migration)

The app code is baked into the image, so new migration files must be copied back to your machine:

```bash
# 1. edit app/models.py, then rebuild so the container has the new models
docker compose up -d --build

# 2. generate the migration inside the container
docker compose exec web flask db migrate -m "Describe your change"

# 3. copy the new file(s) back into your project (then review the file!)
docker compose cp web:/app/migrations/versions/. ./migrations/versions/

# 4. apply it
docker compose exec web flask db upgrade

# 5. commit migrations/versions/*.py to git; the next rebuild bakes them into the image
```

## Seed data

`flask seed` is safe to run any time: it adds sample categories/products **only if both tables are empty**, and creates the admin **only if no admin exists**.

```bash
docker compose exec web flask seed
docker compose exec web flask create-admin      # create/reset an admin (prompts for email + password)
```

## Check PostgreSQL connectivity

```bash
docker compose ps                                   # db should say "healthy"
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'   # list tables
docker compose exec web python -c "import os, psycopg2; psycopg2.connect(os.environ['DATABASE_URL']).close(); print('web -> db connection OK')"
docker compose exec web sh -c 'echo "${DATABASE_URL##*@}"'   # host/db the app uses (password hidden), expect db:5432/stockflow
docker compose exec web flask db current            # confirms SQLAlchemy can reach the DB too
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `POSTGRES_PASSWORD` error when running `docker compose ...` | You have no `.env`. Run `cp .env.example .env`. |
| `password authentication failed for user "postgres"` | The volume was created with an older password. Postgres only reads `POSTGRES_PASSWORD` the *first* time. Either restore the old password in `.env`, or wipe the data: `docker compose down -v && docker compose up -d`. |
| `could not translate host name "db"` | The app is not running through Compose (e.g. plain `docker run`). Use `docker compose up`. Outside Docker, use `localhost` in `DATABASE_URL`. |
| `connection refused` at startup | The entrypoint retries for 60 s. Check `docker compose logs db` and `docker compose ps`. |
| `relation "users" does not exist` | Migrations did not run. Check `docker compose logs web`, then `docker compose exec web flask db upgrade`. |
| Password with `@ : / #` breaks the connection | Passwords go inside a URL. Use letters/digits only, or URL-encode the characters. |
| `port is already allocated` / port 5000 busy (macOS AirPlay uses 5000) | Add `WEB_PORT=5001` to `.env`, then `docker compose up -d`. |
| `exec ./docker-entrypoint.sh: no such file` or `\r` errors | Windows line endings. The Dockerfile already strips them; make sure you rebuilt: `docker compose build --no-cache`. |
| Code changes not showing up | The code is copied into the image: `docker compose up -d --build`. |
| `flask db migrate` says "Target database is not up to date" | `docker compose exec web flask db upgrade` first, then migrate again. |
| Need to start completely fresh | `docker compose down -v && docker compose up -d --build` (deletes all data). |
| Web container restarting | `docker compose logs --tail=100 web` shows the Python error. |
| Connect with DBeaver/psql from your machine | Uncomment the `ports:` lines under `db` in `docker-compose.yml`. |

## Running without Docker (optional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://postgres:change_me@localhost:5432/stockflow SECRET_KEY=dev
export FLASK_APP=run.py
flask db upgrade && flask seed && flask run
```

## What's included

* Landing page, product list with **search by name** and **category filter**, product details
* Signup / login / logout (Flask-Login, passwords hashed with Werkzeug), separate admin login
* Cart: add, increase, decrease, remove, subtotals and total; **quantity can never exceed stock**; visitors who are not logged in are redirected to login/signup when they press "Add to cart"
* Checkout (no payment): creates an `Order` + `OrderItem`s, reduces stock (rows are locked so the last item cannot be sold twice), empties the cart
* Admin: dashboard, category CRUD, product CRUD
* CSRF protection on every form, open-redirect protection on `?next=`

## Production checklist

1. Strong `POSTGRES_PASSWORD` and a long random `SECRET_KEY`
2. Change the admin email/password, set `SEED_ON_START=false`
3. Serve over HTTPS (reverse proxy / load balancer) and set `SESSION_COOKIE_SECURE = True` in `config.py`
4. Do not publish PostgreSQL's port 5432 publicly
# flask-kustomization-k8s
