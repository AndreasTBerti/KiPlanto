from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Path, Query

from model.crop_model import crop_prev, get_model
from schemas.api_schema import DirectPrevisionInput, PrevisionInput, PrevisionOutput, validate_uf
from schemas.cross_schema import CrossRecommendationInput, CrossRecommendationOutput
from services.climate_data_service import (
    CityNotFoundError,
    ClimateProviderError,
    get_climate_data,
    get_coordinates,
)
from services.cross_recommendation import cross_recommend

router = APIRouter(prefix="/ai", tags=["AI & Recomendações"])


def _locate_and_fetch_climate(city: str, state: Optional[str]) -> Tuple[dict, dict]:
    """Geocodifica a cidade e busca o clima, traduzindo falhas em respostas HTTP.

    404: cidade não encontrada (erro de quem chamou).
    502: o Open-Meteo falhou (erro do provedor, não de quem chamou).
    """
    try:
        coords = get_coordinates(city=city, state=state)
        climate = get_climate_data(coords)
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Não foi possível localizar '{city}': {exc}") from exc
    except ClimateProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Serviço meteorológico indisponível ao consultar '{city}': {exc}",
        ) from exc
    return coords, climate


def _build_output(
    result: dict,
    *,
    city: str,
    climate_data: dict,
    state: Optional[str] = None,
    uf: Optional[str] = None,
) -> PrevisionOutput:
    return PrevisionOutput(
        crop_recommendation=result["crop_recommendation"],
        crop_recomendation=result["crop_recommendation"],  # nome antigo, obsoleto
        confidence=result["confidence"],
        city=city,
        state=state,
        uf=uf,
        top_recommendations=result["top_recommendations"],
        climate_data=climate_data,
        features=result["features"],
    )


@router.post("/prevision", response_model=PrevisionOutput)
def get_prevision(data: PrevisionInput):
    coords, climate = _locate_and_fetch_climate(data.city, data.state)

    # O pH (data.ph) não entra: o modelo foi treinado sem essa feature.
    result = crop_prev(
        {
            "N": data.n_ratio,
            "P": data.p_ratio,
            "K": data.k_ratio,
            "temperature": climate["temperature_mean_7d"],
            "humidity": climate["humidity_mean_7d"],
            "rainfall": climate["rainfall_monthly_avg"],
        }
    )

    return _build_output(
        result,
        city=coords["city"],
        state=coords.get("state"),
        uf=coords.get("uf"),
        climate_data=climate,
    )


@router.post("/prevision/direct", response_model=PrevisionOutput)
def get_direct_prevision(data: DirectPrevisionInput):
    result = crop_prev(
        {
            "N": data.n,
            "P": data.p,
            "K": data.k,
            "temperature": data.temperature,
            "humidity": data.humidity,
            "rainfall": data.rainfall,
        }
    )
    return _build_output(
        result,
        city="Manual Input",
        climate_data={
            "temperature": data.temperature,
            "humidity": data.humidity,
            "precipitation": data.rainfall,
            "rainfall_monthly_avg": data.rainfall,
        },
    )


@router.post(
    "/cross-recommendation",
    response_model=CrossRecommendationOutput,
    summary="Cruza a recomendação do modelo com as notícias da região",
    responses={404: {"description": "Cidade não encontrada (ou não encontrada na UF)"}},
)
def get_cross_recommendation(data: CrossRecommendationInput):
    """Fica separada de /ai/prevision porque as notícias podem levar vários segundos."""
    result = crop_prev(
        {
            "N": data.n,
            "P": data.p,
            "K": data.k,
            "temperature": data.temperature,
            "humidity": data.humidity,
            "rainfall": data.rainfall,
        }
    )
    try:
        return cross_recommend(result["probabilities"], city=data.city, uf=data.state)
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Não foi possível localizar '{data.city}': {exc}") from exc


@router.get("/climate/{city}")
def get_city_climate(
    city: str = Path(..., min_length=2, max_length=80, description="Nome do município"),
    state: Optional[str] = Query(None, description="UF (ex.: SP). Opcional; resolve cidades homônimas."),
):
    try:
        uf = validate_uf(state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    coords, climate = _locate_and_fetch_climate(city.strip(), uf)
    return {
        "status": "success",
        "coordinates": coords,
        "climate": climate,
    }


@router.get("/crops")
def list_supported_crops():
    try:
        model = get_model()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar modelo: {exc}") from exc
    classes = [str(c) for c in model.classes_]
    return {
        "total_crops": len(classes),
        "crops": classes,
    }
