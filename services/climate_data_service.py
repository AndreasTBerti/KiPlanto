"""Integração com o Open-Meteo: geocodificação, previsão do tempo e histórico de chuva.

Escalas entregues ao modelo de recomendação (ver model/crop_model.py):
- temperatura e umidade: médias diárias dos próximos 7 dias. A leitura do momento
  varia com a hora da consulta (ex.: 30 °C às 14h contra 24,5 °C de média);
- chuva: média mensal dos últimos 12 meses, em mm/mês. O modelo foi treinado com
  chuva na faixa de ~30–265 mm (escala mensal). A média diária da semana (~0–10 mm),
  usada antes, caía sempre abaixo do menor corte das árvores (P-01 do relatório).
"""

import json
import os
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Hashable, List, Optional

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.br_states import normalize_uf, state_name

load_dotenv()

OPEN_METEO_URL = os.getenv("OPEN_METEO_URL") or "https://api.open-meteo.com/v1/forecast"
GEO_ENCODING_URL = os.getenv("GEO_ENCODING_URL") or "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ARCHIVE_URL = os.getenv("OPEN_METEO_ARCHIVE_URL") or "https://archive-api.open-meteo.com/v1/archive"
HTTP_TIMEOUT_SECONDS = float(os.getenv("CLIMATE_HTTP_TIMEOUT_SECONDS") or 10)

FORECAST_DAYS = 7
RAINFALL_HISTORY_DAYS = 365
# O arquivo do Open-Meteo (reanálise ERA5) é publicado com ~5 dias de atraso.
ARCHIVE_DELAY_DAYS = 7
DAYS_PER_MONTH = 365.25 / 12
# Até 10% de dias sem dado no histórico ainda é aceitável.
MIN_HISTORY_COVERAGE = 0.9

GEOCODING_CACHE_TTL_SECONDS = 24 * 3600
FORECAST_CACHE_TTL_SECONDS = 15 * 60
RAINFALL_CACHE_TTL_SECONDS = 24 * 3600

KNOWN_COORDINATES_FILE = Path(__file__).with_name("municipios_coordenadas.json")


class CityNotFoundError(ValueError):
    """A geocodificação não encontrou a cidade (ou não a encontrou na UF pedida)."""


class ClimateProviderError(RuntimeError):
    """Falha ao consultar o Open-Meteo: timeout, erro HTTP ou resposta inesperada."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _build_session()


def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        response = _session.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ClimateProviderError(f"falha ao consultar {url}: {exc}") from exc


# ---------------------------------------------------------------------------
# Cache em memória (por processo)
# ---------------------------------------------------------------------------

class _TTLCache:
    def __init__(self, max_entries: int = 1024):
        self._data: Dict[Hashable, tuple] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def get(self, key: Hashable) -> Optional[Any]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: Hashable, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            if len(self._data) >= self._max_entries:
                # Descarta a entrada mais antiga (dicts preservam a ordem de inserção).
                self._data.pop(next(iter(self._data)))
            self._data[key] = (time.monotonic() + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_cache = _TTLCache()


def clear_cache() -> None:
    """Esvazia o cache de geocodificação, previsão e chuva (útil em testes)."""
    _cache.clear()


def _coord_key(latitude: float, longitude: float) -> tuple:
    # 3 casas decimais ~ 100 m: mesma cidade, mesma chave.
    return (round(latitude, 3), round(longitude, 3))


# ---------------------------------------------------------------------------
# Geocodificação
# ---------------------------------------------------------------------------

def _fold_name(text: str) -> str:
    """Minúsculas, sem acento e sem pontuação: IBGE e geocodificador grafam diferente
    "Ji-Paraná"/"Ji Paraná" e "D'Oeste"/"d’Oeste"."""
    decomposed = unicodedata.normalize("NFKD", text or "").replace("-", " ")
    kept = "".join(ch for ch in decomposed if not unicodedata.combining(ch) and ch not in "'’")
    return " ".join(kept.casefold().split())


def _load_known_coordinates() -> Dict[tuple, dict]:
    """Centroide dos municípios do IBGE (scripts/gerar_municipios.py), usado quando o
    geocodificador não reconhece uma opção da lista do frontend."""
    data = json.loads(KNOWN_COORDINATES_FILE.read_text(encoding="utf-8"))
    return {
        (uf, _fold_name(city)): {
            "name": city,
            "admin1": state_name(uf),
            "country": "Brasil",
            "latitude": latitude,
            "longitude": longitude,
        }
        for uf, cities in data.items()
        for city, (latitude, longitude) in cities.items()
    }


_known_coordinates = _load_known_coordinates()


def _geocode(city: str, country_code: str) -> List[dict]:
    params = {"count": 10, "language": "pt", "format": "json", "countryCode": country_code}
    return _get_json(GEO_ENCODING_URL, {"name": city, **params}).get("results") or []


def get_coordinates(city: str, country_code: str = "BR", state: Optional[str] = None) -> dict:
    """Resolve a cidade em coordenadas, estado e UF.

    `state` aceita sigla ("SP") ou nome ("São Paulo") e desfaz homônimos
    (ex.: "São José" existe em SC e em outros estados).

    O geocodificador faz busca aproximada ("Tupã" em RS devolveria "Tuparendi").
    Por isso:
    - com UF informada, só aceita nome idêntico ao pedido (ignorando acentos, caixa e
      pontuação); se não houver, usa o centroide do município no IBGE, quando existe;
    - sem UF, prefere o nome idêntico e, se não houver, usa o resultado mais relevante.

    Levanta CityNotFoundError se nada for encontrado e ClimateProviderError
    se o Open-Meteo falhar.
    """
    city = (city or "").strip()
    if not city:
        raise CityNotFoundError("informe o nome da cidade")

    uf = None
    if state is not None and state.strip():
        uf = normalize_uf(state)
        if uf is None:
            raise CityNotFoundError(f"UF inválida: {state}")

    cache_key = ("geo", _fold_name(city), country_code, uf)
    cached = _cache.get(cache_key)
    if cached is not None:
        return dict(cached)

    results = _geocode(city, country_code)
    wanted = _fold_name(city)
    exact = [r for r in results if _fold_name(r.get("name", "")) == wanted]
    if not exact and "'" in city:
        # A busca do geocodificador diferencia ' de ’, e a base dele usa ’.
        results = _geocode(city.replace("'", "’"), country_code) or results
        exact = [r for r in results if _fold_name(r.get("name", "")) == wanted]

    if uf:
        candidates = [r for r in exact if normalize_uf(r.get("admin1")) == uf]
        if not candidates and (uf, wanted) in _known_coordinates:
            candidates = [_known_coordinates[(uf, wanted)]]
        if not candidates:
            raise CityNotFoundError(
                f"cidade não encontrada em {uf}: {city} (confira o nome ou deixe a UF em branco)"
            )
    else:
        candidates = exact or results
        if not candidates:
            raise CityNotFoundError(f"cidade não encontrada: {city}")

    location = candidates[0]

    try:
        admin1 = location.get("admin1")
        location_uf = normalize_uf(admin1)
        coordinates = {
            "city": location["name"],
            "country": location.get("country"),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": location.get("timezone"),
            "state": state_name(location_uf) or admin1,
            "uf": location_uf,
        }
    except (KeyError, TypeError) as exc:
        raise ClimateProviderError(f"resposta inesperada da geocodificação: campo {exc} ausente") from exc

    _cache.set(cache_key, coordinates, GEOCODING_CACHE_TTL_SECONDS)
    return dict(coordinates)


# ---------------------------------------------------------------------------
# Previsão (próximos 7 dias) e histórico de chuva (últimos 12 meses)
# ---------------------------------------------------------------------------

def _mean(values: List[Optional[float]], label: str) -> float:
    valid = [v for v in values if v is not None]
    if not valid:
        raise ClimateProviderError(f"previsão sem valores de {label}")
    return sum(valid) / len(valid)


def get_forecast(latitude: float, longitude: float) -> dict:
    """Condições atuais (para exibição) e agregados dos próximos 7 dias (para o modelo)."""
    cache_key = ("forecast",) + _coord_key(latitude, longitude)
    cached = _cache.get(cache_key)
    if cached is not None:
        return dict(cached)

    data = _get_json(
        OPEN_METEO_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,rain_sum",
            "forecast_days": FORECAST_DAYS,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
        },
    )

    try:
        current = data["current"]
        daily = data["daily"]
        temperature_mean = _mean(daily["temperature_2m_mean"], "temperatura")
        humidity_mean = _mean(daily["relative_humidity_2m_mean"], "umidade")
        precipitation_daily = [v for v in daily["precipitation_sum"] if v is not None]
        rain_daily = [v for v in daily["rain_sum"] if v is not None]
        forecast = {
            # Condições do momento: só para exibição.
            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "wind_direction": current["wind_direction_10m"],
            "precipitation": current["precipitation"],
            "time": current["time"],
            # Agregados dos próximos 7 dias.
            "temperature_mean_7d": round(temperature_mean, 2),
            "humidity_mean_7d": round(humidity_mean, 2),
            "precipitation_total_7d": round(sum(precipitation_daily), 2),
            # OBSOLETOS: nomes antigos, mantidos com o mesmo significado de antes
            # para não quebrar clientes. Use os campos *_7d acima.
            # "preciptation_forecast" e "rain_forecast" são MÉDIAS DIÁRIAS, não totais.
            "temperature_forecast": round(temperature_mean, 2),
            "preciptation_forecast": round(_mean(precipitation_daily, "precipitação"), 2),
            "rain_forecast": round(_mean(rain_daily, "chuva"), 2),
        }
    except (KeyError, TypeError) as exc:
        raise ClimateProviderError(f"resposta inesperada da previsão: campo {exc} ausente") from exc

    _cache.set(cache_key, forecast, FORECAST_CACHE_TTL_SECONDS)
    return dict(forecast)


def get_monthly_rainfall(latitude: float, longitude: float, today: Optional[date] = None) -> float:
    """Chuva média mensal (mm/mês) dos últimos 12 meses, pela API de arquivo do Open-Meteo."""
    today = today or date.today()
    end = today - timedelta(days=ARCHIVE_DELAY_DAYS)
    start = end - timedelta(days=RAINFALL_HISTORY_DAYS - 1)

    cache_key = ("rainfall",) + _coord_key(latitude, longitude) + (end.isoformat(),)
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get_json(
        OPEN_METEO_ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "precipitation_sum",
            "timezone": "auto",
        },
    )

    try:
        values = [v for v in data["daily"]["precipitation_sum"] if v is not None]
    except (KeyError, TypeError) as exc:
        raise ClimateProviderError(f"resposta inesperada do histórico de chuva: campo {exc} ausente") from exc

    if len(values) < RAINFALL_HISTORY_DAYS * MIN_HISTORY_COVERAGE:
        raise ClimateProviderError(
            f"histórico de chuva incompleto: {len(values)} de {RAINFALL_HISTORY_DAYS} dias"
        )

    monthly = round(sum(values) / len(values) * DAYS_PER_MONTH, 2)
    _cache.set(cache_key, monthly, RAINFALL_CACHE_TTL_SECONDS)
    return monthly


def get_climate_data(coordinate_data: dict) -> dict:
    """Clima da localidade: condições atuais, agregados de 7 dias e chuva média mensal.

    Previsão e histórico são buscados em paralelo.
    """
    latitude = coordinate_data["latitude"]
    longitude = coordinate_data["longitude"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        forecast_job = pool.submit(get_forecast, latitude, longitude)
        rainfall_job = pool.submit(get_monthly_rainfall, latitude, longitude)
        forecast = forecast_job.result()
        rainfall_monthly_avg = rainfall_job.result()

    return {
        "city": coordinate_data.get("city"),
        "state": coordinate_data.get("state"),
        "uf": coordinate_data.get("uf"),
        "latitude": latitude,
        "longitude": longitude,
        **forecast,
        "rainfall_monthly_avg": rainfall_monthly_avg,
    }


if __name__ == "__main__":
    location = get_coordinates("Tupã", state="SP")
    print(location)
    print(get_climate_data(location))
