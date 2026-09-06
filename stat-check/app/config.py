from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_path: str
    session_secret: str
    gitea_base_url: str
    gitea_client_id: str
    gitea_client_secret: str
    public_base_url: str
    teacher_logins: frozenset[str]
    base_path: str = "/stat-check"
    secure_cookie: bool = True
    testing: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("SESSION_SECRET", "")
        if not secret:
            raise RuntimeError("SESSION_SECRET is required")
        teachers = frozenset(
            item.strip().casefold()
            for item in os.getenv("TEACHER_LOGINS", "").split(",")
            if item.strip()
        )
        return cls(
            database_path=os.getenv(
                "DATABASE_PATH", "/data/stat-check.sqlite3"
            ),
            session_secret=secret,
            gitea_base_url=os.getenv(
                "GITEA_BASE_URL", "https://hblu.top/gitea"
            ).rstrip("/"),
            gitea_client_id=os.getenv("GITEA_CLIENT_ID", ""),
            gitea_client_secret=os.getenv("GITEA_CLIENT_SECRET", ""),
            public_base_url=os.getenv(
                "PUBLIC_BASE_URL", "https://hblu.top/stat-check"
            ).rstrip("/"),
            teacher_logins=teachers,
            secure_cookie=_as_bool(os.getenv("SECURE_COOKIE"), True),
        )
