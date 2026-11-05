"""Testes de cadastro, login e proteção das rotas."""
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

import main
from services import auth_service

EMAIL = "ana@example.com"
PASSWORD = "uma-senha-de-teste"
ACCOUNT = {"name": "Ana", "email": EMAIL, "password": PASSWORD}

pytestmark = pytest.mark.usefixtures("real_auth")


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, **overrides):
    return client.post("/auth/register", json={**ACCOUNT, **overrides})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


# --- cadastro ----------------------------------------------------------------

def test_register_creates_the_account_and_logs_in(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == EMAIL
    assert body["user"]["name"] == "Ana"
    assert "password" not in str(body)
    assert client.get("/auth/me", headers=bearer(body["token"])).json()["email"] == EMAIL


def test_email_is_unique_ignoring_case_and_spaces(client):
    assert register(client).status_code == 201

    response = register(client, email="  ANA@Example.com ")

    assert response.status_code == 409
    assert "Já existe" in response.json()["detail"]


@pytest.mark.parametrize(
    "override",
    [
        {"name": " "},
        {"name": "x" * 81},
        {"email": "sem-arroba"},
        {"email": "a@b"},
        {"email": "a b@example.com"},
        {"password": "curta"},
        {"password": "x" * 129},
    ],
)
def test_invalid_registration_is_rejected(client, override):
    assert register(client, **override).status_code == 422


def test_registrations_are_limited_per_client(client):
    for index in range(auth_service.MAX_REGISTRATIONS):
        assert register(client, email=f"pessoa{index}@example.com").status_code == 201

    assert register(client, email="mais-uma@example.com").status_code == 429


# --- o que fica no banco -----------------------------------------------------

def stored(tmp_path, query):
    connection = sqlite3.connect(tmp_path / "test.db")
    try:
        return connection.execute(query).fetchall()
    finally:
        connection.close()


def test_password_and_token_are_not_stored_in_clear(client, tmp_path):
    token = register(client).json()["token"]

    [(password_hash,)] = stored(tmp_path, "SELECT password_hash FROM users")
    [(token_hash,)] = stored(tmp_path, "SELECT token_hash FROM sessions")
    assert PASSWORD not in password_hash
    assert password_hash.startswith("scrypt$")
    assert token not in token_hash


def test_same_password_gets_different_hashes():
    assert auth_service.hash_password(PASSWORD) != auth_service.hash_password(PASSWORD)


def test_corrupted_hash_does_not_authenticate():
    assert auth_service.verify_password(PASSWORD, "lixo") is False
    assert auth_service.verify_password(PASSWORD, "scrypt$a$b$c$d$e") is False


# --- login -------------------------------------------------------------------

def test_login_works_with_email_in_any_case(client):
    register(client)

    response = login(client, email=" Ana@EXAMPLE.com ")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == EMAIL


def test_wrong_password_and_unknown_email_look_the_same(client):
    register(client)

    wrong = login(client, password="outra-senha-qualquer")
    unknown = login(client, email="ninguem@example.com")

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert "token" not in wrong.json()


def test_login_is_blocked_after_too_many_attempts(client):
    register(client)

    for _ in range(auth_service.MAX_LOGIN_ATTEMPTS):
        assert login(client, password="senha-errada-aqui").status_code == 401

    # Bloqueado mesmo com a senha certa; outro e-mail segue livre.
    assert login(client).status_code == 429
    assert login(client, email="outra@example.com").status_code == 401


def test_successful_login_resets_the_attempts(client):
    register(client)

    for _ in range(auth_service.MAX_LOGIN_ATTEMPTS - 1):
        login(client, password="senha-errada-aqui")
    assert login(client).status_code == 200

    assert login(client, password="senha-errada-aqui").status_code == 401


def test_oversized_password_is_rejected_before_hashing(client):
    assert login(client, password="x" * 129).status_code == 422


# --- sessão ------------------------------------------------------------------

def test_logout_ends_only_that_session(client):
    register(client)
    first, second = login(client).json()["token"], login(client).json()["token"]

    assert client.post("/auth/logout", headers=bearer(first)).status_code == 204

    assert client.get("/auth/me", headers=bearer(first)).status_code == 401
    assert client.get("/auth/me", headers=bearer(second)).status_code == 200


def test_expired_session_is_refused(client, monkeypatch):
    token = register(client).json()["token"]
    real_time = time.time

    monkeypatch.setattr(auth_service.time, "time", lambda: real_time() + 8 * 24 * 60 * 60)

    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_session_length_comes_from_the_environment(client, monkeypatch):
    monkeypatch.setenv("AUTH_SESSION_DAYS", "1")
    token = register(client).json()["token"]
    real_time = time.time

    monkeypatch.setattr(auth_service.time, "time", lambda: real_time() + 2 * 24 * 60 * 60)

    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer inventado"}, {"Authorization": "Basic abc"}])
def test_me_and_logout_need_a_valid_session(client, headers):
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post("/auth/logout", headers=headers).status_code == 401


# --- rotas protegidas --------------------------------------------------------

FEATURES = {"n": 60, "p": 45, "k": 50, "temperature": 24, "humidity": 70, "rainfall": 120}
PROTECTED = [
    ("post", "/ai/prevision", {"city": "Tupã", "n_ratio": 60, "p_ratio": 45, "k_ratio": 50}),
    ("post", "/ai/prevision/direct", FEATURES),
    ("post", "/ai/cross-recommendation", {"city": "Tupã", **FEATURES}),
    ("get", "/ai/climate/Tupã", None),
    ("get", "/ai/crops", None),
    ("get", "/news?city=Tupã", None),
]


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_app_routes_refuse_requests_without_login(client, method, path, body):
    kwargs = {"json": body} if body else {}

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_every_ai_and_news_route_requires_login(client):
    """Rota nova em /ai ou /news não pode ficar aberta por esquecimento."""
    paths = client.get("/openapi.json").json()["paths"]
    checked = 0
    for path, operations in paths.items():
        if path.startswith(("/ai", "/news")):
            for operation in operations.values():
                assert operation.get("security"), path
                checked += 1
    assert checked >= len(PROTECTED)


def test_valid_session_reaches_a_protected_route(client):
    token = register(client).json()["token"]

    assert client.get("/ai/crops", headers=bearer(token)).status_code == 200


def test_public_routes_stay_open(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200


def test_cors_allows_the_authorization_header(client):
    response = client.options(
        "/ai/crops",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers
