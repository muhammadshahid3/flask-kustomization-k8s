from app import create_app

app = create_app()

if __name__ == "__main__":
    # Only used for running without Docker: `python run.py`
    # Inside Docker the app is started by Gunicorn (run:app).
    app.run(host="0.0.0.0", port=5000)
