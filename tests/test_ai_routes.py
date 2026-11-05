"""Testes das rotas /, /health e /ai/*, com o Open-Meteo simulado (sem rede).

O modelo real (model/modelo_recomendacao_safra.joblib) é carregado.
"""

import pytest
from fastapi.testclient import TestClient

import main
from services import climate_data_service as climate

GEO = {
    "results": [
        {
            "name": "Tupã",
            "admin1": "São Paulo",
            "country": "Brasil",
            "latitude": -21.93472,
            "longitude": -50.51361,
            "timezone": "America/Sao_Paulo",
        },
        {
            "name": "Tupã",
            "admin1": "Pará",
            "country": "Brasil",
            "latitude": -7.1453,
            "longitude": -49.83603,
            "timezone": "America/Belem",
        },
    ]
}

FORECAST = {
    "current": {
        "temperature_2m": 30.1,
        "relative_humidity_2m": 62,
        "wind_speed_10m": 1.8,
        "wind_direction_10m": 53,
        "precipitation": 0.0,
        "time": "2026-11-03T14:00",
    },
    "daily": {
        "temperature_2m_mean": [24.3, 27.9, 27.2, 26.2, 23.9, 22.4, 19.4],
        "relative_humidity_2m_mean": [80, 69, 73, 82, 91, 72, 62],
        "precipitation_sum": [0.0, 0.0, 1.2, 7.2, 5.7, 0.0, 0.0],
        "rain_sum": [0.0, 0.0, 0.5, 2.9, 4.2, 0.0, 0.0],
    },
}

# 4 mm/dia durante 365 dias -> 4 * 365.25 / 12 = 121.75 mm/mês
ARCHIVE = {"daily": {"precipitation_sum": [4.0] * 365}}

SOIL = {"n_ratio": 60, "p_ratio": 45, "k_ratio": 50}
DIRECT = {"n": 80, "p": 40, "k": 40, "temperature": 24, "humidity": 65, "rainfall": 120}


class FakeOpenMeteo:
    def __init__(self):
        self.responses = {
            climate.GEO_ENCODING_URL: GEO,
            climate.OPEN_METEO_URL: FORECAST,
            climate.OPEN_METEO_ARCHIVE_URL: ARCHIVE,
        }

    def fail(self, url, message="timeout simulado"):
        self.responses[url] = climate.ClimateProviderError(message)

    def __call__(self, url, params):
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def meteo(monkeypatch):
    climate.clear_cache()
    fake = FakeOpenMeteo()
    monkeypatch.setattr(climate, "_get_json", fake)
    yield fake
    climate.clear_cache()


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as test_client:
        yield test_client


# --- status ----------------------------------------------------------------

def test_home_lists_the_ai_endpoints(client):
    response = client.get("/")

    assert response.status_code == 200
    paths = {endpoint["path"] for endpoint in response.json()["endpoints"]}
    assert {"/", "/health", "/ai/prevision", "/ai/prevision/direct", "/ai/climate/{city}", "/ai/crops"} <= paths


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_crops_lists_the_22_model_classes(client):
    body = client.get("/ai/crops").json()

    assert body["total_crops"] == 22
    assert "coffee" in body["crops"]


# --- /ai/prevision -----------------------------------------------------------

def test_prevision_feeds_the_model_with_monthly_rainfall_and_7_day_means(client, meteo):
    """P-01 e P-03: a chuva entra em mm/mês; temperatura e umidade, como médias de 7 dias."""
    response = client.post("/ai/prevision", json={"city": "Tupã", "state": "SP", **SOIL})

    assert response.status_code == 200
    body = response.json()
    assert body["features"] == {
        "N": 60.0,
        "P": 45.0,
        "K": 50.0,
        "temperature": 24.47,
        "humidity": 75.57,
        "rainfall": 121.75,
    }
    # O menor corte de rainfall nas árvores é ~30 mm: abaixo disso tudo vira "seco".
    assert body["features"]["rainfall"] > 30
    assert (body["city"], body["state"], body["uf"]) == ("Tupã", "São Paulo", "SP")


def test_prevision_returns_new_and_deprecated_crop_field(client, meteo):
    body = client.post("/ai/prevision", json={"city": "Tupã", **SOIL}).json()

    assert body["crop_recommendation"]
    assert body["crop_recomendation"] == body["crop_recommendation"]


def test_prevision_climate_data_keeps_deprecated_keys(client, meteo):
    climate_data = client.post("/ai/prevision", json={"city": "Tupã", **SOIL}).json()["climate_data"]

    assert climate_data["precipitation_total_7d"] == 14.1
    assert climate_data["preciptation_forecast"] == 2.01  # obsoleto: média diária
    assert climate_data["temperature_forecast"] == 24.47  # obsoleto
    assert climate_data["rainfall_monthly_avg"] == 121.75


def test_prevision_state_resolves_homonyms(client, meteo):
    body = client.post("/ai/prevision", json={"city": "Tupã", "state": "pa", **SOIL}).json()

    assert body["uf"] == "PA"
    assert body["climate_data"]["latitude"] == -7.1453


def test_prevision_without_ph_is_accepted(client, meteo):
    assert client.post("/ai/prevision", json={"city": "Tupã", **SOIL}).status_code == 200


def test_city_not_found_is_404(client, meteo):
    meteo.responses[climate.GEO_ENCODING_URL] = {}

    response = client.post("/ai/prevision", json={"city": "CidadeQueNaoExiste", **SOIL})

    assert response.status_code == 404
    assert "localizar" in response.json()["detail"]


def test_city_not_found_in_state_is_404(client, meteo):
    response = client.post("/ai/prevision", json={"city": "Tupã", "state": "RS", **SOIL})

    assert response.status_code == 404


@pytest.mark.parametrize("failing", ["geo", "forecast", "archive"])
def test_provider_failure_is_502(client, meteo, failing):
    url = {
        "geo": climate.GEO_ENCODING_URL,
        "forecast": climate.OPEN_METEO_URL,
        "archive": climate.OPEN_METEO_ARCHIVE_URL,
    }[failing]
    meteo.fail(url)

    response = client.post("/ai/prevision", json={"city": "Tupã", **SOIL})

    assert response.status_code == 502
    assert "indisponível" in response.json()["detail"]


# --- /ai/prevision/direct ----------------------------------------------------

def test_direct_prevision_uses_the_given_features(client):
    body = client.post("/ai/prevision/direct", json=DIRECT).json()

    assert body["features"] == {
        "N": 80.0,
        "P": 40.0,
        "K": 40.0,
        "temperature": 24.0,
        "humidity": 65.0,
        "rainfall": 120.0,
    }
    assert body["crop_recomendation"] == body["crop_recommendation"]


def test_ph_does_not_change_the_recommendation(client):
    """P-02: o modelo não tem a feature pH. O campo é aceito, mas não influencia."""
    results = [
        client.post("/ai/prevision/direct", json={**DIRECT, **extra}).json()
        for extra in ({}, {"ph": 3.5}, {"ph": 9.0})
    ]

    assert len({(r["crop_recommendation"], r["confidence"]) for r in results}) == 1


# --- validação (P-06) --------------------------------------------------------

@pytest.mark.parametrize(
    "override",
    [
        {"n": -1},
        {"k": 5000},
        {"temperature": 100},
        {"humidity": 101},
        {"humidity": -1},
        {"rainfall": -5},
        {"ph": 15},
    ],
)
def test_direct_prevision_rejects_physically_invalid_values(client, override):
    assert client.post("/ai/prevision/direct", json={**DIRECT, **override}).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"city": "Tupã", "n_ratio": -1, "p_ratio": 45, "k_ratio": 50},
        {"city": "Tupã", "state": "XX", **SOIL},
        {"city": " ", **SOIL},
        {"city": "Tupã", "ph": -2, **SOIL},
        {"city": "Tupã", "n_ratio": 1, "p_ratio": 1},
    ],
)
def test_prevision_rejects_invalid_payloads(client, meteo, payload):
    assert client.post("/ai/prevision", json=payload).status_code == 422


# --- /ai/climate/{city} ------------------------------------------------------

def test_climate_with_state(client, meteo):
    response = client.get("/ai/climate/Tupã", params={"state": "SP"})

    assert response.status_code == 200
    body = response.json()
    assert body["coordinates"]["uf"] == "SP"
    assert body["climate"]["rainfall_monthly_avg"] == 121.75
    assert body["climate"]["humidity_mean_7d"] == 75.57


def test_climate_invalid_state_is_422(client, meteo):
    assert client.get("/ai/climate/Tupã", params={"state": "XX"}).status_code == 422


def test_climate_city_not_found_is_404(client, meteo):
    meteo.responses[climate.GEO_ENCODING_URL] = {"results": []}

    assert client.get("/ai/climate/Inexistente").status_code == 404


# --- CORS (P-07) -------------------------------------------------------------

def preflight(client, origin):
    return client.options(
        "/ai/crops",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_cors_allows_the_frontend_origin(client):
    response = preflight(client, "http://localhost:3000")

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_rejects_unknown_origins(client):
    response = preflight(client, "https://evil.example")

    assert "access-control-allow-origin" not in response.headers
