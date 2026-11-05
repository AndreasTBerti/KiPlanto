"""Ambiente dos testes: sem IA de verdade, com um banco temporário e com login já resolvido.

As rotas de /ai e /news exigem sessão. Quem testa essas rotas recebe um usuário pronto; o próprio
login é exercitado em tests/test_auth.py, com a fixture `real_auth`.
"""
import pytest

import main
from routers.auth_router import require_user
from services import auth_service, llm_reader, openrouter
from services.auth_service import User

TEST_USER = User(id=1, name="Pessoa de Teste", email="teste@kiplanto.test")


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)
    for name in ("OPENROUTER_MAX_SPEND_USD", "OPENROUTER_MAX_INPUT_PRICE", "OPENROUTER_MAX_OUTPUT_PRICE"):
        monkeypatch.delenv(name, raising=False)
    llm_reader.clear_cache()
    openrouter.reset_spend()


@pytest.fixture(autouse=True)
def _temporary_database(monkeypatch, tmp_path):
    monkeypatch.setenv("KIPLANTO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("AUTH_SESSION_DAYS", raising=False)
    auth_service.reset_attempts()


@pytest.fixture(autouse=True)
def _logged_in():
    main.app.dependency_overrides[require_user] = lambda: TEST_USER
    yield
    main.app.dependency_overrides.pop(require_user, None)


@pytest.fixture
def real_auth(_logged_in):
    """Liga de volta a verificação real da sessão."""
    main.app.dependency_overrides.pop(require_user, None)
