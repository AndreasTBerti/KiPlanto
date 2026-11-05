"""GET /news com geocodificação e fontes substituídas (sem rede)."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
from services.climate_data_service import CityNotFoundError, ClimateProviderError
from services.news import service
from services.news.sources import RawItem, SourceResult

client = TestClient(app)
NOW = datetime.now(timezone.utc)
TUPA = {"city": "Tupã", "country": "Brasil", "latitude": -21.93, "longitude": -50.51,
        "timezone": "America/Sao_Paulo", "state": "São Paulo", "uf": "SP"}


def item(feed, title, summary=None, days_ago=1, url=None, image="https://img.example/a.jpg"):
    return RawItem(
        title=title,
        summary=summary,
        url=url or f"https://news.example/{feed}/{abs(hash(title))}",
        source_name=feed,
        source_feed=feed,
        published_at=NOW - timedelta(days=days_ago),
        image_url=image,
    )


FEEDS = {
    "g1_estadual": [
        item("g1_estadual", "Colheita de amendoim avança na região", "Produtores comemoram o clima."),
        item("g1_estadual", "Motociclista morre em acidente na SP-280"),
    ],
    "g1_agro": [
        item("g1_agro", "Colheita de soja avança nos EUA", "Chicago reage."),
        item("g1_agro", "Safra de milho em SP deve crescer 10%", "Conab revisa estimativa.", days_ago=3),
    ],
    "canal_rural": [
        item("canal_rural", "Chuvas podem reduzir safra de trigo de SP", "Setor defende integração.", days_ago=0),
        item("canal_rural", "Safra de cana em SP fechou há meses", days_ago=45),
    ],
    "portal_agronegocio": [
        item("portal_agronegocio", "Plantio de café começa em Tupã", None, days_ago=2, image=None),
        item("portal_agronegocio", "Preço do milho sobe na semana", "Mercado segue firme.", days_ago=1),
    ],
    "globo_rural": [
        item("globo_rural", "Preço do milho cai em SP", "Oferta aumentou.", days_ago=4),
    ],
    "compre_rural": [],
}


class Calls:
    geocoding = 0
    fetches: list = []


@pytest.fixture(autouse=True)
def fake_backends(monkeypatch):
    service.clear_caches()
    Calls.geocoding = 0
    Calls.fetches = []
    failing: set[str] = set()

    def fake_coordinates(city, country_code="BR", state=None):
        Calls.geocoding += 1
        if city.startswith("Inexistente"):
            raise CityNotFoundError(f"cidade não encontrada: {city}")
        if city.startswith("Offline"):
            raise ClimateProviderError("timeout")
        return dict(TUPA)

    def fake_fetch_source(source, location, crop=None, days=30):
        Calls.fetches.append((source.id, crop.id if crop else None, days))
        if source.id in failing:
            return SourceResult(source.id, ok=False, error="timeout após 8s")
        items = FEEDS[source.id]
        return SourceResult(source.id, ok=True, items=list(items), items_fetched=len(items))

    monkeypatch.setattr(service, "get_coordinates", fake_coordinates)
    monkeypatch.setattr(service, "fetch_source", fake_fetch_source)
    monkeypatch.delenv("NEWS_ENABLED_SOURCES", raising=False)
    yield failing
    service.clear_caches()


def get_news(**params):
    params.setdefault("city", "Tupã")
    return client.get("/news", params=params)


def test_full_success_contract():
    response = get_news(state="SP")
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == {"city": "Tupã", "state": "São Paulo", "uf": "SP"}
    assert body["cached"] is False and body["crop"] is None
    titles = [a["title"] for a in body["articles"]]
    # 11 (Tupã) > 10 (SP, 3 termos) > 9 (SP) > 7 (inferred); EUA, acidente e notícia de 45 dias ficam de fora
    assert titles == [
        "Plantio de café começa em Tupã",
        "Safra de milho em SP deve crescer 10%",
        "Chuvas podem reduzir safra de trigo de SP",
        "Colheita de amendoim avança na região",
    ]
    assert [a["relevance_score"] for a in body["articles"]] == [11, 10, 9, 7]
    assert body["total"] == 4
    assert [a["location_match"] for a in body["articles"]] == ["city", "state", "state", "inferred"]
    for article in body["articles"]:  # CA-02, CA-03
        assert article["url"].startswith("https://") and article["matched_keywords"]
        assert len(article["id"]) == 16 and article["crop_match"] is False
        assert datetime.fromisoformat(article["published_at"]) >= NOW - timedelta(days=30)
    kept = {s["source"]: s["items_kept"] for s in body["sources"]}
    assert kept == {
        "g1_estadual": 1, "g1_agro": 1, "canal_rural": 1, "portal_agronegocio": 1, "globo_rural": 0, "compre_rural": 0,
    }
    assert all(s["ok"] for s in body["sources"])


def test_partial_failure_still_200(fake_backends):
    fake_backends.add("canal_rural")
    body = get_news().json()
    status = {s["source"]: s for s in body["sources"]}
    assert status["canal_rural"]["ok"] is False and status["canal_rural"]["error"] == "timeout após 8s"
    assert status["g1_agro"]["ok"] is True
    assert "Chuvas podem reduzir safra de trigo de SP" not in [a["title"] for a in body["articles"]]
    assert body["total"] == 3


def test_all_sources_failing_is_502(fake_backends):
    fake_backends.update(service.SOURCES)
    response = get_news()
    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "Nenhuma fonte de notícias respondeu"
    assert len(body["sources"]) == len(service.SOURCES) and not any(s["ok"] for s in body["sources"])


def test_second_request_comes_from_cache():
    first = get_news(state="SP")
    start = time.perf_counter()
    second = get_news(state="SP")
    elapsed = time.perf_counter() - start
    assert first.json()["cached"] is False and second.json()["cached"] is True
    assert second.json()["articles"] == first.json()["articles"]
    assert Calls.geocoding == 1
    assert elapsed < 0.3  # CA-01


def test_limit_and_days():
    body = get_news(limit=2).json()
    assert body["total"] == 2 and len(body["articles"]) == 2
    assert sum(s["items_kept"] for s in body["sources"]) == 2
    wide = get_news(days=60).json()
    assert "Safra de cana em SP fechou há meses" in [a["title"] for a in wide["articles"]]


def test_crop_from_model_prioritizes_matching_news():
    body = get_news(crop="maize").json()
    assert body["crop"] == {"id": "maize", "name": "Milho", "terms": ["milho"]}
    top = body["articles"][0]
    assert top["title"] == "Safra de milho em SP deve crescer 10%"
    assert top["crop_match"] is True
    # tema 3+1+1 (safra, milho, conab) + SP 3 + recência 2 + bônus da cultura 3
    assert top["relevance_score"] == 13


def test_crop_orders_region_then_other_regions_then_other_crops():
    articles = get_news(crop="maize").json()["articles"]
    summary = [(a["title"], a["location_match"], a["crop_match"]) for a in articles]
    assert summary[:3] == [
        ("Safra de milho em SP deve crescer 10%", "state", True),
        ("Preço do milho cai em SP", "state", True),  # sem termo de colheita: entra pela cultura
        ("Preço do milho sobe na semana", "outside", True),
    ]
    assert all(not crop_match for _, _, crop_match in summary[3:])
    assert all(location != "outside" for _, location, _ in summary[3:])


def test_other_regions_do_not_push_regional_news_off_the_list(monkeypatch):
    many = [item("canal_rural", f"Preço do milho na semana {n}", days_ago=1) for n in range(40)]
    monkeypatch.setitem(FEEDS, "canal_rural", many)
    articles = get_news(crop="maize", limit=30).json()["articles"]
    assert sum(a["location_match"] == "outside" for a in articles) == service.MAX_OUTSIDE_ARTICLES
    assert "Plantio de café começa em Tupã" in [a["title"] for a in articles]


def test_crop_and_days_reach_the_sources():
    get_news(crop="maize", days=60)
    assert ("compre_rural", "maize", 60) in Calls.fetches


def test_crop_is_part_of_cache_key():
    get_news()
    assert get_news(crop="maize").json()["cached"] is False


@pytest.mark.parametrize("params", [
    {"state": "XX"},
    {"state": "São Paulo"},
    {"days": 0},
    {"days": 181},
    {"limit": 31},
    {"crop": "abacaxi"},
    {"city": "a"},
    {"city": "  a  "},
])
def test_invalid_params_are_422(params):
    assert get_news(**params).status_code == 422


def test_lowercase_uf_is_accepted():
    assert get_news(state="sp").status_code == 200


def test_unknown_city_is_404():
    response = get_news(city="Inexistente da Silva")
    assert response.status_code == 404
    assert response.json()["detail"].startswith("Não foi possível localizar 'Inexistente da Silva'")


def test_geocoding_outage_is_502():
    assert get_news(city="Offline").status_code == 502


def test_slow_source_times_out_without_blocking(monkeypatch):
    def slow(source, location, crop=None, days=30):
        time.sleep(1.0)
        return SourceResult(source.id, ok=True)

    monkeypatch.setattr(service, "fetch_source", slow)
    monkeypatch.setattr(service, "COLLECT_DEADLINE_SECONDS", 0.2)
    start = time.perf_counter()
    response = get_news()
    assert time.perf_counter() - start < 0.9
    assert response.status_code == 502
    assert all(s["error"].startswith("timeout") for s in response.json()["sources"])


def test_enabled_sources_from_env(monkeypatch):
    monkeypatch.setenv("NEWS_ENABLED_SOURCES", "canal_rural, portal_agronegocio,desconhecida")
    sources = [s["source"] for s in get_news().json()["sources"]]
    assert sources == ["canal_rural", "portal_agronegocio"]


def test_home_lists_news_endpoint():
    paths = [e["path"] for e in client.get("/").json()["endpoints"]]
    assert "/news" in paths
