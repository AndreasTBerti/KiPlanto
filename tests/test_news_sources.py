"""Parse dos feeds reais salvos em tests/fixtures/news (sem rede) e camada HTTP."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from services.news import http
from services.news.crops import get_crop
from services.news.sources import (
    SOURCES,
    Location,
    fetch_source,
    html_to_text,
    parse_feed,
    parse_search,
    safe_http_url,
    search_url,
    truncate_words,
)

FIXTURES = Path(__file__).parent / "fixtures" / "news"
TUPA = Location(city="Tupã", state="São Paulo", uf="SP")
CASES = [
    ("g1_sp.xml", "g1_estadual"),
    ("g1_agro.xml", "g1_agro"),
    ("canal_rural.xml", "canal_rural"),
    ("portal_agronegocio.xml", "portal_agronegocio"),
]


def parse(fixture, source_id):
    return parse_feed((FIXTURES / fixture).read_bytes(), SOURCES[source_id])


@pytest.fixture(autouse=True)
def _clear_feed_cache():
    http.feed_cache.clear()
    yield
    http.feed_cache.clear()


@pytest.mark.parametrize("fixture, source_id", CASES)
def test_every_item_is_clean(fixture, source_id):
    items, total = parse(fixture, source_id)
    assert items and total >= len(items)
    for item in items:
        assert item.title and item.source_feed == source_id
        assert safe_http_url(item.url) == item.url
        assert item.published_at is not None and item.published_at.tzinfo is not None
        assert item.summary is None or ("<" not in item.summary and len(item.summary) <= 500)
        assert item.image_url is None or item.image_url.startswith("https://")


def test_g1_drops_publieditorial_and_uses_subtitle_as_lead():
    items, total = parse("g1_sp.xml", "g1_estadual")
    assert total == 5 and len(items) == 3  # 2 itens de /especial-publicitario/
    assert all("/especial-publicitario/" not in i.url for i in items)
    first = items[0]
    assert first.summary.startswith("Acidente ocorreu na manhã desta terça-feira (3).")
    assert first.image_url.startswith("https://s2-g1.glbimg.com/")  # media:content


def test_g1_agro_lead_is_not_the_full_article():
    items, _ = parse("g1_agro.xml", "g1_agro")
    uva = next(i for i in items if "Jales" in i.title)
    assert uva.summary == (
        "Variedade criada pela Embrapa já ocupa 600 hectares e deve movimentar R$ 130 milhões na safra."
    )


def test_canal_rural_summary_without_photo_credit_and_wordpress_footer():
    items, _ = parse("canal_rural.xml", "canal_rural")
    trigo = next(i for i in items if "trigo" in i.title)
    assert trigo.summary == (
        "Precipitações em setembro prejudicaram a produção e a qualidade dos grãos; "
        "setor defende maior integração entre produtores e indústria moageira"
    )
    assert trigo.image_url == "https://imagens-cdn.canalrural.com.br/2024/10/reMslFQ2-clouds-194840_960_720.jpg"
    for item in items:
        assert "Foto:" not in item.summary
        assert "apareceu primeiro em" not in item.summary


def test_portal_agronegocio_image_from_item_image_tag():
    items, _ = parse("portal_agronegocio.xml", "portal_agronegocio")
    assert all(i.image_url and "/storage/images/notices/" in i.image_url for i in items)
    assert items[0].source_name == "Portal do Agronegócio"


def test_html_to_text_and_truncate():
    assert html_to_text("<p>Olá <b>mundo</b></p><script>x()</script>") == "Olá mundo"
    text = "palavra " * 100
    cut = truncate_words(text.strip())
    assert len(cut) <= 500 and cut.endswith("palavra…")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "/relativo", "ftp://x.com/a", None, 3])
def test_safe_http_url_rejects_non_http(url):
    assert safe_http_url(url) is None


def test_g1_state_feed_url_uses_uf():
    assert SOURCES["g1_estadual"].feed_url(TUPA) == "https://g1.globo.com/rss/g1/sp/"
    assert SOURCES["g1_estadual"].feed_url(Location(city="X")) is None


# --- fetch_source (http.fetch substituído) ------------------------------------------

def test_empty_feed_counts_as_failure(monkeypatch):
    content = (FIXTURES / "g1_vazio.xml").read_bytes()
    monkeypatch.setattr(http, "fetch", lambda url: http.FetchResult(content=content, cached=False))
    result = fetch_source(SOURCES["g1_estadual"], TUPA)
    assert (result.ok, result.error, result.items) == (False, "feed vazio ou inexistente", [])


def test_fetch_error_becomes_source_status(monkeypatch):
    def boom(url):
        raise http.FetchError("HTTP 429")

    monkeypatch.setattr(http, "fetch", boom)
    result = fetch_source(SOURCES["canal_rural"], TUPA)
    assert (result.ok, result.error) == (False, "HTTP 429")


def test_state_feed_without_uf_fails_without_request(monkeypatch):
    monkeypatch.setattr(http, "fetch", lambda url: pytest.fail("não deveria baixar"))
    result = fetch_source(SOURCES["g1_estadual"], Location(city="X"))
    assert not result.ok and "estado" in result.error


def test_successful_fetch_reports_counts(monkeypatch):
    content = (FIXTURES / "canal_rural.xml").read_bytes()
    monkeypatch.setattr(http, "fetch", lambda url: http.FetchResult(content=content, cached=True))
    result = fetch_source(SOURCES["canal_rural"], TUPA)
    assert result.ok and result.cached and result.items_fetched == 10 and len(result.items) == 10


# --- http.fetch: User-Agent, erros e cache por URL ---------------------------------

class FakeResponse:
    def __init__(self, status_code=200, content=b"<rss/>"):
        self.status_code = status_code
        self.content = content


class FakeSession:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_fetch_caches_by_url(monkeypatch):
    session = FakeSession(FakeResponse(content=b"feed"))
    monkeypatch.setattr(http, "_session", lambda: session)
    first = http.fetch("https://feed.example/rss")
    second = http.fetch("https://feed.example/rss")
    assert (first.cached, second.cached, second.content) == (False, True, b"feed")
    assert session.calls == [("https://feed.example/rss", http.HTTP_TIMEOUT_SECONDS)]


@pytest.mark.parametrize("outcome, message", [
    (requests.Timeout(), f"timeout após {http.HTTP_TIMEOUT_SECONDS}s"),
    (requests.ConnectionError(), "falha de conexão (ConnectionError)"),
    (FakeResponse(status_code=403), "HTTP 403"),
])
def test_fetch_errors(monkeypatch, outcome, message):
    monkeypatch.setattr(http, "_session", lambda: FakeSession(outcome))
    with pytest.raises(http.FetchError, match=message.replace("(", r"\(").replace(")", r"\)")):
        http.fetch("https://feed.example/rss")
    assert http.feed_cache.get("https://feed.example/rss") is None  # falha não entra no cache


def test_session_sends_identifiable_user_agent():
    assert http._session().headers["User-Agent"].startswith("KiPlantoBot/1.0 (+https://github.com/")


# --- busca por cultura (API REST do WordPress) ----------------------------------------

POSTS = [
    {
        "date_gmt": "2026-11-04T14:58:45",
        "link": "https://www.comprerural.com/preco-do-mamao/",
        "title": {"rendered": "Pre&ccedil;o do mam&atilde;o sobe em SP"},
        "excerpt": {"rendered": "<p>Oferta menor na semana.</p>\n", "protected": False},
        "yoast_head_json": {"og_image": [{"url": "https://www.comprerural.com/a.png"}]},
    },
    {"date_gmt": "invalida", "link": "javascript:alert(1)", "title": {"rendered": "Sem link válido"}},
    {"date_gmt": None, "link": "https://www.comprerural.com/sem-data/", "title": {"rendered": "Sem data"}},
]


def test_search_url_uses_only_the_crop_term_and_a_fixed_host():
    url = search_url(SOURCES["compre_rural"], get_crop("papaya"), 30)
    assert url.startswith("https://www.comprerural.com/wp-json/wp/v2/posts?")
    assert "search=mam%C3%A3o" in url and "T00%3A00%3A00" in url


def test_parse_search_normalizes_posts_and_skips_invalid():
    items, total = parse_search(json.dumps(POSTS).encode(), SOURCES["compre_rural"])
    assert total == 3 and [i.title for i in items] == ["Preço do mamão sobe em SP", "Sem data"]
    first = items[0]
    assert first.summary == "Oferta menor na semana."
    assert first.image_url == "https://www.comprerural.com/a.png"
    assert first.published_at == datetime(2026, 11, 4, 14, 58, 45, tzinfo=timezone.utc)
    assert items[1].published_at is None and items[1].image_url is None and items[1].summary is None


@pytest.mark.parametrize("content", [b"<html>erro</html>", b'{"code": "rest_no_route"}'])
def test_invalid_search_response_becomes_source_status(monkeypatch, content):
    monkeypatch.setattr(http, "fetch", lambda url: http.FetchResult(content=content, cached=False))
    result = fetch_source(SOURCES["compre_rural"], TUPA, get_crop("papaya"))
    assert result.ok is False and result.error == "resposta de busca inválida"


def test_search_with_no_results_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(http, "fetch", lambda url: http.FetchResult(content=b"[]", cached=False))
    result = fetch_source(SOURCES["compre_rural"], TUPA, get_crop("jute"))
    assert result.ok is True and result.items == []


def test_source_with_search_reads_the_feed_when_no_crop_is_given(monkeypatch):
    urls = []

    def fake_fetch(url):
        urls.append(url)
        raise http.FetchError("HTTP 500")

    monkeypatch.setattr(http, "fetch", fake_fetch)
    fetch_source(SOURCES["compre_rural"], TUPA)
    assert urls == ["https://www.comprerural.com/feed/"]
