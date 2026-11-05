"""Schemas de resposta de GET /news (SPEC §5.6)."""
from datetime import datetime
from typing import List, Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

SourceFeed = Literal["g1_estadual", "g1_agro", "canal_rural", "portal_agronegocio", "globo_rural", "compre_rural"]
# outside: cita a cultura pedida, mas não menciona a região (só com `crop`).
LocationMatch = Literal["city", "state", "inferred", "outside"]


def _is_http_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc)


class NewsLocation(BaseModel):
    city: str
    state: Optional[str] = None
    uf: Optional[str] = None


class NewsCrop(BaseModel):
    id: str = Field(..., description="Classe do modelo de ML (ex.: maize)")
    name: str = Field(..., description="Nome em português (ex.: Milho)")
    terms: List[str] = Field(..., description="Termos procurados nas notícias")


class NewsArticle(BaseModel):
    id: str = Field(..., description="sha1(url canônica)[:16]")
    title: str
    summary: Optional[str] = Field(None, max_length=500, description="Texto puro, sem HTML")
    url: str
    source_name: str
    source_feed: SourceFeed
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None
    location_match: LocationMatch
    matched_keywords: List[str]
    crop_match: bool = Field(False, description="O texto cita a cultura pedida em `crop`")
    relevance_score: float

    @field_validator("url")
    @classmethod
    def _url_http(cls, value: str) -> str:
        if not _is_http_url(value):
            raise ValueError("url precisa ser http(s)")
        return value

    @field_validator("image_url")
    @classmethod
    def _image_http(cls, value: Optional[str]) -> Optional[str]:
        return value if value and _is_http_url(value) else None


class SourceStatus(BaseModel):
    source: SourceFeed
    ok: bool
    items_fetched: int
    items_kept: int
    cached: bool
    error: Optional[str] = None


class NewsResponse(BaseModel):
    location: NewsLocation
    generated_at: datetime
    cached: bool
    total: int
    crop: Optional[NewsCrop] = None
    articles: List[NewsArticle]
    sources: List[SourceStatus]
