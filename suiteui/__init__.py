try:
    from .celery import app as celery_app

    __all__ = ["celery_app"]
except Exception:
    # Celery is optional at import-time for the Django app.
    # If it's not installed, the UI can still run in synchronous fallback mode.
    __all__ = []
