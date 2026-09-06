import os
import tempfile


os.environ.setdefault("SESSION_SECRET", "test-import-secret")
os.environ.setdefault(
    "DATABASE_PATH", f"{tempfile.gettempdir()}/stat-check-import.sqlite3"
)
os.environ.setdefault("SECURE_COOKIE", "false")
