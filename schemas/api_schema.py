from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PrevisionInput(BaseModel):
    city: str = Field(..., description="Nome da cidade para consulta climática")
    n_ratio: float = Field(..., description="Taxa de Nitrogênio (N) no solo")
    p_ratio: float = Field(..., description="Taxa de Fósforo (P) no solo")
    k_ratio: float = Field(..., description="Taxa de Potássio (K) no solo")
    ph: float = Field(..., description="Nível de pH do solo")

class TopRecommendation(BaseModel):
    crop: str
    probability: float

class PrevisionOutput(BaseModel):
    crop_recomendation: str
    confidence: Optional[float] = None
    city: Optional[str] = None
    top_recommendations: Optional[List[TopRecommendation]] = None
    climate_data: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, float]] = None

class DirectPrevisionInput(BaseModel):
    n: float
    p: float
    k: float
    temperature: float
    humidity: float
    rainfall: float
    ph: Optional[float] = 6.5