from fastapi import APIRouter, HTTPException
from model.crop_model import crop_prev, get_model
from schemas.api_schema import PrevisionInput, PrevisionOutput, DirectPrevisionInput
from services.climate_data_service import get_coordinates, get_climate_data

router = APIRouter(prefix="/ai", tags=["AI & Recomendações"])

@router.post("/prevision", response_model=PrevisionOutput)
def get_prev(data: PrevisionInput):
    try:
        coords = get_coordinates(city=data.city)
        climate = get_climate_data(coords)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível obter dados meteorológicos para '{data.city}': {str(e)}"
        )
    
    model_input = {
        "N": data.n_ratio,
        "P": data.p_ratio,
        "K": data.k_ratio,
        "temperature": climate.get("temperature", climate.get("temperature_forecast", 25.0)),
        "humidity": climate.get("humidity", 70.0),
        "rainfall": climate.get("preciptation_forecast", climate.get("precipitation", 100.0)),
    }
    
    result = crop_prev(model_input)
    
    return PrevisionOutput(
        crop_recomendation=result["crop_recomendation"],
        confidence=result.get("confidence"),
        city=coords.get("city", data.city),
        top_recommendations=result.get("top_recommendations"),
        climate_data=climate,
        features=result.get("features")
    )

@router.post("/prevision/direct", response_model=PrevisionOutput)
def get_direct_prev(data: DirectPrevisionInput):
    model_input = {
        "N": data.n,
        "P": data.p,
        "K": data.k,
        "temperature": data.temperature,
        "humidity": data.humidity,
        "rainfall": data.rainfall,
    }
    result = crop_prev(model_input)
    return PrevisionOutput(
        crop_recomendation=result["crop_recomendation"],
        confidence=result.get("confidence"),
        city="Manual Input",
        top_recommendations=result.get("top_recommendations"),
        climate_data={
            "temperature": data.temperature,
            "humidity": data.humidity,
            "precipitation": data.rainfall
        },
        features=result.get("features")
    )

@router.get("/climate/{city}")
def get_city_climate(city: str):
    try:
        coords = get_coordinates(city=city)
        climate = get_climate_data(coords)
        return {
            "status": "success",
            "coordinates": coords,
            "climate": climate
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Falha ao consultar clima para '{city}': {str(e)}"
        )

@router.get("/crops")
def list_supported_crops():
    try:
        model = get_model()
        classes = list(model.classes_)
        return {
            "total_crops": len(classes),
            "crops": classes
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao carregar modelo: {str(e)}"
        )