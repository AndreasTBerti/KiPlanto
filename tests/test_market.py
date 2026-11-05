"""GET /market com o IBGE substituído (sem rede)."""
import pytest
from fastapi.testclient import TestClient

from main import app
from model.crop_model import get_model
from services import market_service

client = TestClient(app)

MUNICIPALITIES = [
    {"id": 3555000, "nome": "Tupã"},
    {"id": 3555109, "nome": "Tupi Paulista"},
]


def variable(var_id, by_locality):
    return {
        "id": var_id,
        "resultados": [
            {"series": [{"localidade": {"id": loc}, "serie": serie} for loc, serie in by_locality.items()]}
        ],
    }


def payload(yields, production, area, value):
    return [
        variable("112", yields),
        variable("214", production),
        variable("216", area),
        variable("215", value),
    ]


MAIZE = payload(
    yields={"1": {"2025": "6376"}, "35": {"2025": "5870"}, "3555000": {"2025": "3000"}},
    production={"1": {"2025": "141209998"}, "35": {"2025": "4231182"}, "3555000": {"2025": "3000"}},
    area={"1": {"2025": "22145776"}, "35": {"2025": "720868"}, "3555000": {"2025": "1000"}},
    value={"1": {"2025": "122109852"}, "35": {"2025": "4594593"}, "3555000": {"2025": "3000"}},
)


@pytest.fixture
def ibge(monkeypatch):
    """Devolve `ibge.aggregates` e registra os parâmetros de cada consulta aos agregados."""

    class Fake:
        aggregates = MAIZE
        queries: list = []
        municipality_calls = 0

    Fake.queries = []
    Fake.municipality_calls = 0

    def fake_get_json(url, params=None):
        if "localidades/estados" in url:
            Fake.municipality_calls += 1
            return MUNICIPALITIES
        Fake.queries.append(params)
        return Fake.aggregates

    market_service.clear_cache()
    monkeypatch.setattr(market_service, "_get_json", fake_get_json)
    yield Fake
    market_service.clear_cache()


def get(**params):
    return client.get("/market", params=params)


def test_city_state_and_country_in_order_with_derived_numbers(ibge):
    body = get(crop="maize", city="Tupã", state="SP").json()

    assert [level["scope"] for level in body["levels"]] == ["city", "state", "country"]
    assert ibge.queries[0]["localidades"] == "N1[all]|N3[35]|N6[3555000]"
    assert ibge.queries[0]["classificacao"] == "782[40122]"

    city = body["levels"][0]
    assert city["name"] == "Tupã"
    assert city["year"] == 2025
    assert city["yield_per_ha"] == 3000
    assert city["price"] == 1.0  # R$ 3 milhões ÷ 3 mil t
    assert city["revenue_per_ha"] == 3000  # R$ 3 milhões ÷ 1 mil ha

    assert body["levels"][2]["price"] == 0.86
    assert body["crop_name"] == "Milho"
    assert body["unit"] == "kg"
    assert body["approximate"] is False


def test_city_name_ignores_accents_and_case(ibge):
    assert get(crop="maize", city="TUPA", state="sp").json()["levels"][0]["name"] == "Tupã"


def test_city_without_production_falls_back_to_state_and_country(ibge):
    ibge.aggregates = payload(
        yields={"1": {"2025": "6376"}, "35": {"2025": "5870"}, "3555000": {"2025": "-"}},
        production={"1": {"2025": "141209998"}, "35": {"2025": "4231182"}, "3555000": {"2025": "-"}},
        area={"1": {"2025": "22145776"}, "35": {"2025": "720868"}, "3555000": {"2025": "-"}},
        value={"1": {"2025": "122109852"}, "35": {"2025": "4594593"}, "3555000": {"2025": "-"}},
    )
    body = get(crop="maize", city="Tupã", state="SP").json()
    assert [level["scope"] for level in body["levels"]] == ["state", "country"]


def test_latest_year_with_data_is_used_when_the_last_one_is_missing(ibge):
    ibge.aggregates = payload(
        yields={"1": {"2023": "889", "2024": "1308", "2025": "..."}},
        production={"1": {"2023": "6000", "2024": "6540", "2025": "..."}},
        area={"1": {"2023": "6750", "2024": "5000", "2025": "..."}},
        value={"1": {"2023": "4000", "2024": "4802", "2025": "..."}},
    )
    level = get(crop="jute").json()["levels"][0]
    assert level["year"] == 2024
    assert level["yield_per_ha"] == 1308


def test_missing_value_keeps_yield_but_leaves_price_empty(ibge):
    ibge.aggregates = payload(
        yields={"1": {"2025": "6376"}},
        production={"1": {"2025": "1000"}},
        area={"1": {"2025": "500"}},
        value={"1": {"2025": "X"}},
    )
    level = get(crop="maize").json()["levels"][0]
    assert level["yield_per_ha"] == 6376
    assert level["price"] is None
    assert level["revenue_per_ha"] is None


def test_no_state_queries_only_the_country(ibge):
    ibge.aggregates = payload(
        yields={"1": {"2025": "6376"}},
        production={"1": {"2025": "1000"}},
        area={"1": {"2025": "500"}},
        value={"1": {"2025": "860"}},
    )
    body = get(crop="maize", city="Tupã").json()
    assert ibge.queries[0]["localidades"] == "N1[all]"
    assert ibge.municipality_calls == 0
    assert [level["scope"] for level in body["levels"]] == ["country"]


def test_unknown_city_keeps_state_and_country(ibge):
    get(crop="maize", city="Cidade Que Não Existe", state="SP")
    assert ibge.queries[0]["localidades"] == "N1[all]|N3[35]"


def test_coconut_is_counted_in_fruits(ibge):
    assert get(crop="coconut").json()["unit"] == "fruto"


def test_bean_varieties_are_marked_as_approximate(ibge):
    body = get(crop="mungbean").json()
    assert body["approximate"] is True
    assert body["product"] == "Feijão (em grão)"


def test_crop_outside_the_survey_answers_without_querying(ibge):
    body = get(crop="lentil", city="Tupã", state="SP").json()
    assert body["product"] is None
    assert body["levels"] == []
    assert ibge.queries == []


def test_result_is_cached(ibge):
    get(crop="maize", city="Tupã", state="SP")
    get(crop="maize", city="Tupã", state="SP")
    assert len(ibge.queries) == 1
    assert ibge.municipality_calls == 1


def test_unknown_crop_is_rejected(ibge):
    assert get(crop="soja").status_code == 422


def test_invalid_state_is_rejected(ibge):
    assert get(crop="maize", state="ZZ").status_code == 422


def test_provider_failure_becomes_502(monkeypatch):
    def failing(url, params=None):
        raise market_service.MarketProviderError("timeout")

    market_service.clear_cache()
    monkeypatch.setattr(market_service, "_get_json", failing)
    response = get(crop="maize")
    assert response.status_code == 502
    assert "timeout" in response.json()["detail"]


def test_malformed_payload_becomes_502(ibge):
    ibge.aggregates = [{"id": "112"}]
    assert get(crop="maize").status_code == 502


def test_products_cover_every_model_class():
    classes = {str(c) for c in get_model().classes_}
    assert classes <= set(market_service.PRODUCTS)
