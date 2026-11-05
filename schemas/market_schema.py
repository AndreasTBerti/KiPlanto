"""Schemas de resposta de GET /market."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MarketLevel(BaseModel):
    scope: Literal["city", "state", "country"]
    name: str = Field(..., description="Município, UF ou Brasil")
    year: int = Field(..., description="Ano da leitura: o mais recente com produção, nos últimos 3 anos")
    yield_per_ha: float = Field(..., description="Rendimento médio, em kg/ha (frutos/ha se unit for fruto)")
    harvested_area_ha: float = Field(..., description="Área colhida, em hectares")
    production: float = Field(..., description="Quantidade produzida, em toneladas (mil frutos se unit for fruto)")
    price: Optional[float] = Field(
        None, description="Valor da produção ÷ quantidade, em R$/kg (R$/fruto). Média do ano, não é cotação do dia"
    )
    revenue_per_ha: Optional[float] = Field(
        None, description="Valor da produção ÷ área colhida, em R$/ha. Receita bruta, sem descontar custos"
    )


class MarketOutput(BaseModel):
    crop: str = Field(..., description="Classe do modelo de ML (ex.: maize)")
    crop_name: str = Field(..., description="Nome em português (ex.: Milho)")
    product: Optional[str] = Field(None, description="Produto no IBGE. Vazio: o IBGE não acompanha esta cultura")
    approximate: bool = Field(False, description="O dado é de um produto mais amplo que a cultura (ex.: feijão)")
    unit: Literal["kg", "fruto"] = "kg"
    levels: List[MarketLevel] = Field(..., description="Município, estado e Brasil, nesta ordem, só os que têm dado")
    source: str
    source_url: str
