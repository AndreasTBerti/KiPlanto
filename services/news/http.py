"""Cliente HTTP da coleta: User-Agent identificável, timeout por requisição e cache por URL.

Só baixa URLs montadas em `sources.py`: hosts fixos e termos de busca vindos de CROPS.
Nenhum texto livre do cliente vira URL (proteção contra SSRF, SPEC §5.10).
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Hashable, Optional

import requests
from dotenv import load_dotenv

# As variáveis NEWS_* são lidas na importação; não dependa da ordem de imports do main.py.
load_dotenv()

USER_AGENT = "KiPlantoBot/1.0 (+https://github.com/AndreasTBerti/KiPlanto; projeto academico)"


def env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


HTTP_TIMEOUT_SECONDS = env_int("NEWS_HTTP_TIMEOUT_SECONDS", 8)
FEED_CACHE_TTL_SECONDS = env_int("NEWS_FEED_CACHE_TTL_SECONDS", 900)


class TTLCache:
    """Cache em memória, por processo, com expiração por entrada e limite de tamanho."""

    def __init__(self, max_entries: int = 256) -> None:
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def get(self, key: Hashable) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: Hashable, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            now = time.monotonic()
            if key not in self._data and len(self._data) >= self._max_entries:
                for stale in [k for k, (exp, _) in self._data.items() if exp <= now]:
                    del self._data[stale]
                if len(self._data) >= self._max_entries:
                    # dict preserva ordem de inserção: descarta a entrada mais antiga.
                    del self._data[next(iter(self._data))]
            self._data[key] = (now + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class FetchError(Exception):
    """Falha ao baixar um feed. A mensagem vai para `sources[].error` na resposta."""


@dataclass(frozen=True)
class FetchResult:
    content: bytes
    cached: bool


feed_cache = TTLCache()
_local = threading.local()


def _session() -> requests.Session:
    # Uma Session por thread: requests.Session não é garantidamente thread-safe.
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.5",
        })
        _local.session = session
    return session


def fetch(url: str) -> FetchResult:
    """Baixa `url` (com cache de NEWS_FEED_CACHE_TTL_SECONDS). Levanta FetchError em falha.

    Respostas 403/429 não são contornadas (sem troca de User-Agent, proxy ou retry
    agressivo): a fonte só fica marcada como indisponível.
    """
    cached = feed_cache.get(url)
    if cached is not None:
        return FetchResult(content=cached, cached=True)

    try:
        response = _session().get(url, timeout=HTTP_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise FetchError(f"timeout após {HTTP_TIMEOUT_SECONDS}s") from exc
    except requests.RequestException as exc:
        raise FetchError(f"falha de conexão ({type(exc).__name__})") from exc

    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}")

    feed_cache.set(url, response.content, FEED_CACHE_TTL_SECONDS)
    return FetchResult(content=response.content, cached=False)
