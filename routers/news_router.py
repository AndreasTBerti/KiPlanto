from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import AfterValidator

from schemas.news_schema import NewsResponse
from services.br_states import BR_STATES
from services.climate_data_service import CityNotFoundError, ClimateProviderError
from services.news.crops import CROPS
from services.news.service import NewsUnavailableError, get_harvest_news

router = APIRouter(prefix="/news", tags=["Notícias"])


def _clean_city(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("informe ao menos 2 caracteres")
    return value


def _valid_uf(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    uf = value.strip().upper()
    if uf not in BR_STATES:
        raise ValueError(f"UF inválida: {value}")
    return uf


def _valid_crop(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    crop = value.strip().lower()
    if crop not in CROPS:
        raise ValueError(f"cultura desconhecida: {value} (use uma classe de GET /ai/crops)")
    return crop


CityParam = Annotated[
    str,
    Query(min_length=2, max_length=80, description="Nome do município", examples=["Tupã"]),
    AfterValidator(_clean_city),
]
StateParam = Annotated[
    Optional[str],
    Query(min_length=2, max_length=2, description="UF (ex.: SP). Sem UF, vale a geocodificação."),
    AfterValidator(_valid_uf),
]
CropParam = Annotated[
    Optional[str],
    Query(
        max_length=30,
        description="Cultura recomendada pelo modelo (classe de /ai/crops, ex.: maize). "
        "Busca notícias da cultura: primeiro na região, depois em outras regiões.",
    ),
    AfterValidator(_valid_crop),
]


@router.get(
    "",
    response_model=NewsResponse,
    summary="Notícias de colheita por cidade/UF",
    responses={
        404: {"description": "Cidade não encontrada (ou não encontrada na UF)"},
        502: {"description": "Todas as fontes de notícias (ou a geocodificação) falharam"},
    },
)
def list_harvest_news(
    city: CityParam,
    state: StateParam = None,
    days: Annotated[int, Query(ge=1, le=180, description="Janela em dias")] = 30,
    limit: Annotated[int, Query(ge=1, le=30, description="Máximo de artigos")] = 10,
    crop: CropParam = None,
):
    try:
        return get_harvest_news(city, uf=state, days=days, limit=limit, crop=crop)
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Não foi possível localizar '{city}': {exc}") from exc
    except ClimateProviderError as exc:
        raise HTTPException(
            status_code=502, detail=f"Falha na geocodificação de '{city}': {exc}"
        ) from exc
    except NewsUnavailableError as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc), "sources": jsonable_encoder(exc.sources)},
        )
