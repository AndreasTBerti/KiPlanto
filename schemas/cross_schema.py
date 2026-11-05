"""Schemas de POST /ai/cross-recommendation (modelo x notícias da região)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.api_schema import DirectPrevisionInput, validate_uf
from schemas.news_schema import NewsResponse

# news: cita a cultura na região · alert: idem, com termo de risco · generic_news: só cita o termo
# genérico ("feijão") · no_news: nada na região · unavailable: a busca de notícias falhou.
CandidateStatus = Literal["news", "alert", "generic_news", "no_news", "unavailable"]
# Do ponto de vista de quem produz: positive (preço em alta, safra boa), negative, mixed (os dois) ou neutral.
ArticleSentiment = Literal["positive", "negative", "mixed", "neutral"]
OutlookSentiment = Literal["positive", "negative", "mixed", "neutral", "no_news", "unavailable"]


class CrossRecommendationInput(DirectPrevisionInput):
    """As 6 features de `features` em POST /ai/prevision, mais o local das notícias."""

    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    city: str = Field(..., min_length=2, max_length=80, description="Nome do município")
    state: Optional[str] = Field(None, description="UF do município (ex.: SP)")

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: Optional[str]) -> Optional[str]:
        return validate_uf(value)


class CrossAlert(BaseModel):
    article_id: str
    title: str
    terms: List[str] = Field(..., description="Termos de risco citados; palavra-chave, confira a notícia")


class ClassifiedArticle(BaseModel):
    article_id: str
    title: str
    regional: bool = Field(..., description="Fala da região pedida")
    sentiment: ArticleSentiment
    signals: List[str] = Field(..., description="Palavras que decidiram o sentimento")
    classified_by: Literal["llm", "rules"] = Field(..., description="IA ou regras locais")


class CropOutlook(BaseModel):
    """O que o classificador leu nas notícias de uma cultura."""

    sentiment: OutlookSentiment
    scope: Optional[Literal["region", "other_regions"]] = Field(
        None, description="De onde veio a leitura: a região tem prioridade"
    )
    positive: int = Field(..., description="Notícias favoráveis nesse escopo")
    negative: int = Field(..., description="Notícias desfavoráveis nesse escopo")
    neutral: int = Field(..., description="Notícias sem sinal claro ou com sinais divididos nesse escopo")
    text: str = Field(..., description="Resumo da leitura em uma frase")
    articles: List[ClassifiedArticle] = Field(..., description="Só as notícias que são mesmo da cultura")


class CrossCandidate(BaseModel):
    crop: str = Field(..., description="Classe do modelo")
    name: str = Field(..., description="Nome em português")
    probability: float = Field(..., description="Probabilidade do modelo, em %")
    model_rank: int = Field(..., description="Posição na ordem do modelo (1 = primeira)")
    regional_news: int = Field(..., description="Notícias da região sobre a cultura")
    status: CandidateStatus
    summary: str
    alerts: List[CrossAlert]
    outlook: CropOutlook
    news: Optional[NewsResponse] = Field(None, description="Ausente quando a busca de notícias falhou")


class CitedCrop(BaseModel):
    crop: str
    name: str
    mentions: int = Field(..., description="Notícias da região que citam a cultura")
    probability: float = Field(..., description="Probabilidade do modelo, em %")


class CrossReport(BaseModel):
    """Junta a predição do modelo com a leitura das notícias de cada candidata."""

    conclusion: str
    conclusion_by: Literal["llm", "rules"] = Field("rules", description="Quem escreveu a conclusão")
    model: Optional[str] = Field(None, description="Modelo de IA usado nesta consulta, se algum respondeu")
    caveat: str = Field(..., description="Limites da leitura, para aparecer junto da conclusão")


class CrossRecommendationOutput(BaseModel):
    model_recommendation: str = Field(..., description="Primeira cultura pela ordem do modelo")
    recommendation: str = Field(..., description="Primeira cultura depois do cruzamento")
    changed: bool = Field(..., description="As notícias mudaram a primeira colocada")
    explanation: str
    report: CrossReport
    candidates: List[CrossCandidate] = Field(..., description="As até 3 primeiras do modelo, na ordem final")
    also_cited: List[CitedCrop] = Field(..., description="Citadas na região, fora das candidatas")
