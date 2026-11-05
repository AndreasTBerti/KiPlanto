"""Testes de services/climate_data_service.py e services/br_states.py, sem rede."""

import json
from datetime import date
from pathlib import Path

import pytest
import requests

from services import climate_data_service as climate
from services.br_states import BR_STATES, normalize_uf, state_name


def place(name, admin1, lat=-21.9, lon=-50.5):
    return {
        "name": name,
        "admin1": admin1,
        "country": "Brasil",
        "latitude": lat,
        "longitude": lon,
        "timezone": "America/Sao_Paulo",
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


class FakeApi:
    """Substitui climate._get_json: responde por URL e registra as chamadas."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, url, params):
        self.calls.append((url, params))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def _clean_cache():
    climate.clear_cache()
    yield
    climate.clear_cache()


def install(monkeypatch, **responses_by_kind):
    urls = {
        "geo": climate.GEO_ENCODING_URL,
        "forecast": climate.OPEN_METEO_URL,
        "archive": climate.OPEN_METEO_ARCHIVE_URL,
    }
    fake = FakeApi({urls[kind]: value for kind, value in responses_by_kind.items()})
    monkeypatch.setattr(climate, "_get_json", fake)
    return fake


# --- br_states -------------------------------------------------------------

def test_br_states_has_27_ufs_with_g1_feed():
    assert len(BR_STATES) == 27
    assert all(info["g1_feed"] == uf.lower() for uf, info in BR_STATES.items())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SP", "SP"),
        (" sp ", "SP"),
        ("São Paulo", "SP"),
        ("sao paulo", "SP"),
        ("Pará", "PA"),
        ("Estado de Goiás", "GO"),
        ("Mato Grosso do Sul", "MS"),
        ("Mato Grosso", "MT"),
        ("XX", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_uf(value, expected):
    assert normalize_uf(value) == expected


def test_state_name():
    assert state_name("sp") == "São Paulo"
    assert state_name("XX") is None


# --- get_coordinates -------------------------------------------------------

def test_get_coordinates_keeps_old_keys_and_adds_state_and_uf(monkeypatch):
    install(monkeypatch, geo={"results": [place("Tupã", "São Paulo")]})

    coords = climate.get_coordinates("Tupã")

    assert {"city", "country", "latitude", "longitude", "timezone"} <= coords.keys()
    assert coords["state"] == "São Paulo"
    assert coords["uf"] == "SP"


def test_homonym_is_resolved_by_state(monkeypatch):
    """CA-07 da SPEC: "São José" com state="SC" escolhe Santa Catarina."""
    install(
        monkeypatch,
        geo={
            "results": [
                place("São José", "Rio Grande do Sul", lat=-1.0),
                place("São José", "Santa Catarina", lat=-27.6),
            ]
        },
    )

    coords = climate.get_coordinates("São José", state="SC")

    assert coords["uf"] == "SC"
    assert coords["latitude"] == -27.6


def test_without_state_exact_name_wins_over_more_relevant_fuzzy_match(monkeypatch):
    install(
        monkeypatch,
        geo={"results": [place("São José dos Campos", "São Paulo"), place("São José", "Santa Catarina")]},
    )

    assert climate.get_coordinates("sao jose")["city"] == "São José"


def test_without_state_falls_back_to_most_relevant_result(monkeypatch):
    install(monkeypatch, geo={"results": [place("Embu das Artes", "São Paulo")]})

    assert climate.get_coordinates("Embu")["city"] == "Embu das Artes"


def test_with_state_fuzzy_match_is_rejected(monkeypatch):
    """O geocodificador devolve "Tuparendi" para "Tupã" em RS; isso não é a cidade pedida."""
    install(monkeypatch, geo={"results": [place("Tuparendi", "Rio Grande do Sul")]})

    with pytest.raises(climate.CityNotFoundError, match="em RS"):
        climate.get_coordinates("Tupã", state="RS")


@pytest.mark.parametrize("ibge, geocoder, admin1, uf", [
    ("Ji-Paraná", "Ji Paraná", "Rondônia", "RO"),
    ("Diamante D'Oeste", "Diamante d’Oeste", "Paraná", "PR"),
    ("Olhos-d'Água", "Olhos d'Água", "Minas Gerais", "MG"),
])
def test_ibge_name_matches_geocoder_spelling(monkeypatch, ibge, geocoder, admin1, uf):
    install(monkeypatch, geo={"results": [place(geocoder, admin1)]})

    assert climate.get_coordinates(ibge, state=uf)["city"] == geocoder


def test_straight_apostrophe_is_retried_with_the_curly_one(monkeypatch):
    def fake(url, params):
        return {"results": [place("Sítio d’Abadia", "Goiás")]} if "’" in params["name"] else {}

    monkeypatch.setattr(climate, "_get_json", fake)

    assert climate.get_coordinates("Sítio d'Abadia", state="GO")["uf"] == "GO"


def test_municipality_unknown_to_geocoder_uses_ibge_coordinates(monkeypatch):
    install(monkeypatch, geo={})

    location = climate.get_coordinates("Belem do Sao Francisco", state="PE")
    assert location["city"] == "Belém do São Francisco"
    assert -10 < location["latitude"] < -7 and -41 < location["longitude"] < -35
    assert (location["state"], location["uf"]) == ("Pernambuco", "PE")

    with pytest.raises(climate.CityNotFoundError):
        climate.get_coordinates("Belém do São Francisco", state="SP")


def test_geocoder_result_wins_over_ibge_coordinates(monkeypatch):
    install(monkeypatch, geo={"results": [place("Tupã", "São Paulo", lat=-21.93, lon=-50.51)]})

    assert climate.get_coordinates("Tupã", state="SP")["latitude"] == -21.93


def test_every_municipality_in_the_frontend_list_has_coordinates(monkeypatch):
    """Nenhuma opção do seletor pode resultar em "cidade não encontrada"."""
    install(monkeypatch, geo={})
    path = Path(climate.__file__).parent.parent / "frontend" / "src" / "constants" / "municipios.json"
    cities = json.loads(path.read_text(encoding="utf-8"))

    assert len(cities) == 27
    for uf, names in cities.items():
        for name in names:
            assert (uf, climate._fold_name(name)) in climate._known_coordinates, f"{name}/{uf}"


def test_city_not_found(monkeypatch):
    install(monkeypatch, geo={})

    with pytest.raises(climate.CityNotFoundError):
        climate.get_coordinates("CidadeQueNaoExiste")


def test_invalid_state_is_city_not_found(monkeypatch):
    install(monkeypatch, geo={"results": [place("Tupã", "São Paulo")]})

    with pytest.raises(climate.CityNotFoundError, match="UF inválida"):
        climate.get_coordinates("Tupã", state="XX")


def test_uf_is_none_when_admin1_is_not_a_brazilian_state(monkeypatch):
    install(monkeypatch, geo={"results": [place("Lugar", "Região Desconhecida")]})

    coords = climate.get_coordinates("Lugar")

    assert coords["uf"] is None
    assert coords["state"] == "Região Desconhecida"


def test_geocoding_is_cached(monkeypatch):
    fake = install(monkeypatch, geo={"results": [place("Tupã", "São Paulo")]})

    climate.get_coordinates("Tupã")
    climate.get_coordinates(" tupa ")

    assert len(fake.calls) == 1


# --- previsão, chuva e get_climate_data ------------------------------------

def test_forecast_uses_daily_means_and_true_7_day_total(monkeypatch):
    install(monkeypatch, forecast=FORECAST)

    forecast = climate.get_forecast(-21.9, -50.5)

    assert forecast["temperature"] == 30.1  # leitura do momento, só para exibição
    assert forecast["temperature_mean_7d"] == 24.47
    assert forecast["humidity_mean_7d"] == 75.57
    assert forecast["precipitation_total_7d"] == 14.1
    # Campos obsoletos mantêm o significado antigo (médias diárias).
    assert forecast["temperature_forecast"] == 24.47
    assert forecast["preciptation_forecast"] == 2.01
    assert forecast["rain_forecast"] == 1.09


def test_forecast_with_unexpected_payload_is_provider_error(monkeypatch):
    install(monkeypatch, forecast={"current": {}})

    with pytest.raises(climate.ClimateProviderError):
        climate.get_forecast(-21.9, -50.5)


def test_monthly_rainfall_is_mean_daily_times_days_per_month(monkeypatch):
    fake = install(monkeypatch, archive={"daily": {"precipitation_sum": [4.0] * 365}})

    rainfall = climate.get_monthly_rainfall(-21.9, -50.5, today=date(2026, 11, 3))

    assert rainfall == round(4.0 * 365.25 / 12, 2)  # 121.75 mm/mês
    params = fake.calls[0][1]
    assert params["end_date"] == "2026-10-27"  # 7 dias de atraso do ERA5
    assert params["start_date"] == "2025-10-28"  # 365 dias, inclusive


def test_monthly_rainfall_ignores_missing_days(monkeypatch):
    install(monkeypatch, archive={"daily": {"precipitation_sum": [3.0] * 340 + [None] * 25}})

    assert climate.get_monthly_rainfall(0, 0, today=date(2026, 11, 3)) == round(3.0 * 365.25 / 12, 2)


def test_monthly_rainfall_rejects_incomplete_history(monkeypatch):
    install(monkeypatch, archive={"daily": {"precipitation_sum": [3.0] * 300 + [None] * 65}})

    with pytest.raises(climate.ClimateProviderError, match="incompleto"):
        climate.get_monthly_rainfall(0, 0, today=date(2026, 11, 3))


def test_get_climate_data_merges_forecast_and_rainfall(monkeypatch):
    install(monkeypatch, forecast=FORECAST, archive={"daily": {"precipitation_sum": [4.0] * 365}})
    coords = {"city": "Tupã", "state": "São Paulo", "uf": "SP", "latitude": -21.9, "longitude": -50.5}

    data = climate.get_climate_data(coords)

    assert data["city"] == "Tupã"
    assert data["uf"] == "SP"
    assert data["rainfall_monthly_avg"] == 121.75
    assert data["temperature_mean_7d"] == 24.47


def test_provider_error_in_one_source_propagates(monkeypatch):
    install(
        monkeypatch,
        forecast=FORECAST,
        archive=climate.ClimateProviderError("timeout simulado"),
    )

    with pytest.raises(climate.ClimateProviderError, match="timeout simulado"):
        climate.get_climate_data({"latitude": 0, "longitude": 0})


# --- _get_json ---------------------------------------------------------------

def test_get_json_wraps_network_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.Timeout("lento demais")

    monkeypatch.setattr(climate._session, "get", boom)

    with pytest.raises(climate.ClimateProviderError, match="lento demais"):
        climate._get_json("https://exemplo.invalid", {})


def test_get_json_wraps_http_errors(monkeypatch):
    class Response:
        def raise_for_status(self):
            raise requests.HTTPError("500 Server Error")

    monkeypatch.setattr(climate._session, "get", lambda *a, **k: Response())

    with pytest.raises(climate.ClimateProviderError, match="500"):
        climate._get_json("https://exemplo.invalid", {})
