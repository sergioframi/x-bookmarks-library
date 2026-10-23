from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("DATABASE_PATH","/app/data/library.sqlite3"))
    username: str = os.getenv("APP_USERNAME","admin")
    password_hash: str = os.getenv("APP_PASSWORD_HASH","")
    session_secret: str = os.getenv("SESSION_SECRET","")
    session_hours: int = int(os.getenv("SESSION_HOURS","168"))
    cookie_secure: bool = os.getenv("COOKIE_SECURE","false").lower()=="true"
    x_account_id: str = os.getenv("X_ACCOUNT_ID","")
    imports_dir: Path = Path(os.getenv("IMPORTS_DIR","/app/imports"))
    sync_archive_dir: Path = Path(os.getenv("SYNC_ARCHIVE_DIR","/app/data/sync-archives"))
    extension_zip: Path = Path(os.getenv("EXTENSION_ZIP","/app/app/assets/xarchive-connector.zip"))
    session_secret_path: Path = Path(os.getenv("SESSION_SECRET_PATH","/app/data/session-secret"))


settings=Settings()


def ensure_session_secret(current:Settings=settings)->str:
    """Load or create the installation secret in the persistent data volume."""
    configured=current.session_secret.strip()
    if configured and configured!="REPLACE_WITH_RANDOM_SECRET":return configured
    path=current.session_secret_path
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        persisted=path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        persisted=""
    if not persisted:
        generated=secrets.token_urlsafe(48)
        try:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:
            persisted=path.read_text(encoding="utf-8").strip()
        else:
            with os.fdopen(descriptor,"w",encoding="utf-8") as handle:handle.write(generated+"\n")
            persisted=generated
    if len(persisted)<32:raise RuntimeError("El secreto persistente de sesión no es válido")
    object.__setattr__(current,"session_secret",persisted)
    return persisted
