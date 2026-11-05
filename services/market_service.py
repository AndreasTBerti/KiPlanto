"""Preço e produtividade por cultura, a partir da Produção Agrícola Municipal (PAM) do IBGE.

Fonte: API de agregados do IBGE, tabela 5457 (dado público, sem chave). A pesquisa é anual, então
o "preço" aqui é o valor da produção dividido pela quantidade produzida naquele ano: o quanto o
produtor recebeu em média, não a cotação do dia.

Só consulta URLs montadas aqui: hosts fixos, código de produto de PRODUCTS e código de município
vindo do próprio IBGE. Nenhum texto livre do cliente vira URL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.climate_data_service import _fold_name
from services.news.crops import CROPS
from services.news.http import USER_AGENT, TTLCache

# Os 3 anos mais recentes: a juta, por exemplo, ainda não tem dado de 2025.
AGGREGATES_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/5457/periodos/-3/variaveis/112|214|216|215"
MUNICIPALITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
SOURCE_URL = "https://sidra.ibge.gov.br/tabela/5457"
SOURCE_NAME = "IBGE, Produção Agrícola Municipal (tabela 5457)"

VAR_YIELD = "112"  # Rendimento médio: kg/ha (frutos/ha nos produtos contados em frutos)
VAR_PRODUCTION = "214"  # Quantidade produzida: t (mil frutos)
VAR_AREA = "216"  # Área colhida: ha
VAR_VALUE = "215"  # Valor da produção: mil R$

HTTP_TIMEOUT_SECONDS = 15
# A pesquisa é anual e a lista de municípios quase não muda.
CACHE_TTL_SECONDS = 24 * 3600


class MarketProviderError(RuntimeError):
    """Falha ao consultar o IBGE: timeout, erro HTTP ou resposta inesperada."""


@dataclass(frozen=True)
class Product:
    code: int
    name: str
    unit: Literal["kg", "fruto"] = "kg"
    # O dado é de um produto mais amplo que a cultura do modelo.
    approximate: bool = False


# Classe do modelo → produto da PAM. As chaves cobrem model.classes_ (ver tests/test_market.py).
# None: o IBGE não acompanha a cultura. As variedades de feijão do dataset não têm linha própria.
_BEANS = Product(40112, "Feijão (em grão)", approximate=True)
PRODUCTS: dict[str, Optional[Product]] = {
    "apple": Product(40260, "Maçã"),
    "banana": Product(40136, "Banana (cacho)"),
    "blackgram": _BEANS,
    "chickpea": None,
    "coconut": Product(40145, "Coco-da-baía", unit="fruto"),
    "coffee": Product(40139, "Café (em grão)"),
    "cotton": Product(40099, "Algodão herbáceo (em caroço)"),
    "grapes": Product(40274, "Uva"),
    "jute": Product(40115, "Juta (fibra)"),
    "kidneybeans": _BEANS,
    "lentil": None,
    "maize": Product(40122, "Milho (em grão)"),
    "mango": Product(40262, "Manga"),
    "mothbeans": _BEANS,
    "mungbean": _BEANS,
    "muskmelon": Product(40121, "Melão"),
    "orange": Product(40151, "Laranja"),
    "papaya": Product(40261, "Mamão"),
    "pigeonpeas": None,
    "pomegranate": None,
    "rice": Product(40102, "Arroz (em casca)"),
    "watermelon": Product(40120, "Melancia"),
}


def _build_session() -> requests.Session:
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


_session = _build_session()
_cache = TTLCache()


def clear_cache() -> None:
    """Esvazia o cache (útil em testes)."""
    global _cache
    _cache = TTLCache()


def _get_json(url: str, params: Optional[dict[str, str]] = None) -> Any:
    try:
        response = _session.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MarketProviderError(f"falha ao consultar o IBGE: {exc}") from exc


def _municipalities(uf: str) -> list[dict]:
    key = ("municipalities", uf)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    data = _get_json(MUNICIPALITIES_URL.format(uf=uf))
    if not isinstance(data, list):
        raise MarketProviderError("resposta inesperada do IBGE na lista de municípios")
    _cache.set(key, data, CACHE_TTL_SECONDS)
    return data


def _number(raw: Any) -> Optional[float]:
    """O IBGE usa "-" para zero, "..." para sem dado e "X" para dado sob sigilo."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _series_by_locality(payload: Any) -> dict[str, dict[str, dict[str, Any]]]:
    """Localidade → variável → ano → valor."""
    table: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        for variable in payload:
            for result in variable["resultados"]:
                for series in result["series"]:
                    locality = str(series["localidade"]["id"])
                    table.setdefault(locality, {})[str(variable["id"])] = series["serie"]
    except (TypeError, KeyError) as exc:
        raise MarketProviderError(f"resposta inesperada do IBGE: {exc!r}") from exc
    return table


def _build_level(scope: str, name: str, series: dict[str, dict[str, Any]]) -> Optional[dict]:
    """A leitura do ano mais recente com produção de verdade; sem nenhum, None."""
    years = sorted(series.get(VAR_YIELD, {}), reverse=True)
    for year in years:
        yield_per_ha = _number(series.get(VAR_YIELD, {}).get(year))
        production = _number(series.get(VAR_PRODUCTION, {}).get(year))
        area = _number(series.get(VAR_AREA, {}).get(year))
        if not (yield_per_ha and production and area):
            continue
        value = _number(series.get(VAR_VALUE, {}).get(year))
        return {
            "scope": scope,
            "name": name,
            "year": int(year),
            "yield_per_ha": yield_per_ha,
            "harvested_area_ha": area,
            "production": production,
            # mil R$ ÷ t = R$/kg, e mil R$ ÷ mil frutos = R$/fruto.
            "price": round(value / production, 2) if value else None,
            "revenue_per_ha": round(value * 1000 / area) if value else None,
        }
    return None


def get_crop_market(crop: str, *, city: Optional[str] = None, uf: Optional[str] = None) -> dict:
    """Leituras do município, do estado e do Brasil, nesta ordem, só das que têm dado.

    Sem `uf`, só dá para consultar o Brasil. Um município fora da lista do IBGE não é erro:
    a resposta traz o estado e o Brasil.
    """
    product = PRODUCTS[crop]
    response: dict[str, Any] = {
        "crop": crop,
        "crop_name": CROPS[crop].name,
        "product": product.name if product else None,
        "approximate": product.approximate if product else False,
        "unit": product.unit if product else "kg",
        "levels": [],
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
    }
    if product is None:
        return response

    city_id: Optional[str] = None
    city_name: Optional[str] = None
    state_id: Optional[str] = None
    if uf:
        municipalities = _municipalities(uf)
        if municipalities:
            state_id = str(municipalities[0]["id"])[:2]
        wanted = _fold_name(city or "")
        for municipality in municipalities:
            if wanted and _fold_name(municipality["nome"]) == wanted:
                city_id, city_name = str(municipality["id"]), municipality["nome"]
                break

    key = ("levels", product.code, city_id, state_id)
    cached = _cache.get(key)
    if cached is not None:
        return {**response, "levels": cached}

    localities = ["N1[all]"]
    if state_id:
        localities.append(f"N3[{state_id}]")
    if city_id:
        localities.append(f"N6[{city_id}]")
    payload = _get_json(
        AGGREGATES_URL,
        {"localidades": "|".join(localities), "classificacao": f"782[{product.code}]"},
    )
    table = _series_by_locality(payload)

    candidates = [
        ("city", city_name, city_id),
        ("state", uf, state_id),
        ("country", "Brasil", "1"),
    ]
    levels = [
        level
        for scope, name, locality in candidates
        if name and locality and (level := _build_level(scope, name, table.get(locality, {})))
    ]
    _cache.set(key, levels, CACHE_TTL_SECONDS)
    return {**response, "levels": levels}
