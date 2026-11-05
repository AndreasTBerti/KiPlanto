from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.br_states import normalize_uf

# Limites de validade FÍSICA das entradas. Valores válidos, mas fora da faixa em
# que o modelo distingue valores (limiares das árvores: N 0,5–126; P 7–144,5;
# K 14,5–202,5 mg/kg; 16–37 °C; 18–96 %; 30–265 mm/mês), são aceitos: o
# Random Forest apenas satura nos extremos.
NUTRIENT_MAX = 1000.0  # mg/kg
RAINFALL_MAX = 5000.0  # mm/mês


def validate_uf(value: Optional[str]) -> Optional[str]:
    """Normaliza a UF ("sp", "São Paulo" -> "SP"); vazio vira None; inválida é erro."""
    if value is None or not value.strip():
        return None
    uf = normalize_uf(value)
    if uf is None:
        raise ValueError(f"UF inválida: {value!r}")
    return uf


class PrevisionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    city: str = Field(..., min_length=2, max_length=80, description="Nome do município")
    state: Optional[str] = Field(
        None, description="UF do município (ex.: SP). Opcional; resolve cidades homônimas."
    )
    n_ratio: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Nitrogênio (N) no solo, mg/kg")
    p_ratio: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Fósforo (P) no solo, mg/kg")
    k_ratio: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Potássio (K) no solo, mg/kg")
    ph: Optional[float] = Field(
        None, ge=0, le=14, description="pH do solo. Aceito, mas NÃO usado pelo modelo atual."
    )

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: Optional[str]) -> Optional[str]:
        return validate_uf(value)


class TopRecommendation(BaseModel):
    crop: str
    probability: float


class PrevisionOutput(BaseModel):
    crop_recommendation: str = Field(..., description="Cultura recomendada (classe do modelo)")
    crop_recomendation: Optional[str] = Field(
        None,
        deprecated=True,
        description="OBSOLETO: grafia antiga de crop_recommendation, mantida para compatibilidade.",
    )
    confidence: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    uf: Optional[str] = None
    top_recommendations: Optional[List[TopRecommendation]] = None
    climate_data: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, float]] = Field(
        None, description="Valores efetivamente entregues ao modelo (N, P, K, temperature, humidity, rainfall)"
    )


class DirectPrevisionInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    n: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Nitrogênio (N), mg/kg")
    p: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Fósforo (P), mg/kg")
    k: float = Field(..., ge=0, le=NUTRIENT_MAX, description="Potássio (K), mg/kg")
    temperature: float = Field(..., ge=-50, le=60, description="Temperatura média, °C")
    humidity: float = Field(..., ge=0, le=100, description="Umidade relativa média, %")
    rainfall: float = Field(..., ge=0, le=RAINFALL_MAX, description="Chuva média mensal, mm/mês")
    ph: Optional[float] = Field(None, ge=0, le=14, description="Aceito, mas NÃO usado pelo modelo atual.")
