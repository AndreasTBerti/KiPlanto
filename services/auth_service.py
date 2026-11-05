"""Contas e sessões em SQLite, sem dependências além da biblioteca padrão.

- Senha: scrypt com sal aleatório; a senha em si nunca é gravada.
- Sessão: token aleatório entregue uma vez ao navegador; o banco guarda só o hash dele, então uma
  cópia do banco não permite entrar em nenhuma conta.
- Tentativas: contadas em memória, por processo, antes de conferir a senha.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from services.news.http import TTLCache, env_int

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kiplanto.db"
DEFAULT_SESSION_DAYS = 7

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16

MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_REGISTRATIONS = 20
REGISTER_WINDOW_SECONDS = 60 * 60

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
"""

_ready_paths: set[str] = set()
_ready_lock = threading.Lock()
_attempts = TTLCache(max_entries=4096)
_attempts_lock = threading.Lock()


class EmailAlreadyRegistered(Exception):
    """Já existe uma conta com este e-mail."""


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str


def _db_path() -> Path:
    return Path(os.getenv("KIPLANTO_DB_PATH") or DEFAULT_DB_PATH)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    with _ready_lock:
        if str(path) not in _ready_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(path) as setup:
                setup.executescript(_SCHEMA)
            setup.close()
            _ready_paths.add(str(path))
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encoded_salt}${encoded_digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = _derive(password, base64.b64decode(salt), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


# Conferida quando o e-mail não existe, para o tempo de resposta não revelar quem tem conta.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_seconds() -> int:
    return env_int("AUTH_SESSION_DAYS", DEFAULT_SESSION_DAYS) * 24 * 60 * 60


def create_user(name: str, email: str, password: str) -> User:
    """Levanta EmailAlreadyRegistered se o e-mail já tem conta."""
    normalized = normalize_email(email)
    password_hash = hash_password(password)
    connection = _connect()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, normalized, password_hash, int(time.time())),
            )
    except sqlite3.IntegrityError as exc:
        raise EmailAlreadyRegistered(normalized) from exc
    finally:
        connection.close()
    return User(id=cursor.lastrowid, name=name, email=normalized)


def authenticate(email: str, password: str) -> Optional[User]:
    """A conta, se e-mail e senha conferem. Não diz qual dos dois estava errado."""
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (normalize_email(email),),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return User(id=row["id"], name=row["name"], email=row["email"])


def create_session(user: User) -> str:
    """O token só existe aqui e no navegador; o banco guarda o hash."""
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    connection = _connect()
    try:
        with connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_hash_token(token), user.id, now + _session_seconds()),
            )
    finally:
        connection.close()
    return token


def user_from_token(token: str) -> Optional[User]:
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT users.id, users.name, users.email
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (_hash_token(token), int(time.time())),
        ).fetchone()
    finally:
        connection.close()
    return User(id=row["id"], name=row["name"], email=row["email"]) if row else None


def delete_session(token: str) -> None:
    connection = _connect()
    try:
        with connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
    finally:
        connection.close()


def _take_attempt(key: tuple[str, ...], limit: int, window_seconds: int) -> bool:
    """Conta a tentativa e diz se ela está dentro do limite. Conta antes, para valer em pedidos simultâneos."""
    with _attempts_lock:
        used = _attempts.get(key) or 0
        if used >= limit:
            return False
        _attempts.set(key, used + 1, window_seconds)
        return True


def take_login_attempt(client: str, email: str) -> bool:
    return _take_attempt(("login", client, normalize_email(email)), MAX_LOGIN_ATTEMPTS, LOGIN_WINDOW_SECONDS)


def clear_login_attempts(client: str, email: str) -> None:
    with _attempts_lock:
        _attempts.set(("login", client, normalize_email(email)), 0, 1)


def take_registration_attempt(client: str) -> bool:
    return _take_attempt(("register", client), MAX_REGISTRATIONS, REGISTER_WINDOW_SECONDS)


def reset_attempts() -> None:
    _attempts.clear()
