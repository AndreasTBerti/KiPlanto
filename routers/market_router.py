from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

from schemas.api_schema import validate_uf
from schemas.market_schema import MarketOutput
from services.market_service import PRODUCTS, MarketProviderError, get_crop_market

router = APIRouter(prefix="/market", tags=["Preço e produtividade"])


@router.get(
    "",
    response_model=MarketOutput,
    summary="Preço recebido e produção por hectare de uma cultura",
    responses={
        422: {"description": "Cultura ou UF inválida"},
        502: {"description": "O IBGE não respondeu"},
    },
)
def get_market(
    crop: Annotated[str, Query(max_length=30, description="Classe de /ai/crops (ex.: maize)")],
    city: Annotated[Optional[str], Query(max_length=80, description="Município; precisa da UF")] = None,
    state: Annotated[Optional[str], Query(description="UF (ex.: SP). Sem UF, só o dado do Brasil.")] = None,
):
    """Dados anuais do IBGE: o preço é o recebido em média no ano, não a cotação do dia."""
    crop_id = crop.strip().lower()
    if crop_id not in PRODUCTS:
        raise HTTPException(status_code=422, detail=f"cultura desconhecida: {crop} (use uma classe de GET /ai/crops)")
    try:
        uf = validate_uf(state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return get_crop_market(crop_id, city=city, uf=uf)
    except MarketProviderError as exc:
        raise HTTPException(status_code=502, detail=f"O IBGE não respondeu: {exc}") from exc
