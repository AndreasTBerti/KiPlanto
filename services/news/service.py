"""Orquestra a coleta: resolve o local, baixa as fontes em paralelo, ranqueia e cacheia (SPEC §3)."""
from __future__ import annotations

import logging
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Optional

from schemas.news_schema import NewsArticle, NewsCrop, NewsLocation, NewsResponse, SourceStatus
from services.br_states import BR_STATES
from services.climate_data_service import get_coordinates
from services.news import http
from services.news.crops import CropProfile, get_crop
from services.news.relevance import (
    CropMatcher,
    LocationMatcher,
    ScoredItem,
    article_id,
    deduplicate,
    normalize,
    rank,
    score_item,
    within_window,
)
from services.news.sources import SOURCES, Location, Source, SourceResult, fetch_source

logger = logging.getLogger(__name__)

RESPONSE_CACHE_TTL_SECONDS = http.env_int("NEWS_CACHE_TTL_SECONDS", 1800)
# Resposta parcial (alguma fonte falhou) expira antes, para a fonte voltar logo que responder.
PARTIAL_RESPONSE_TTL_SECONDS = min(120, RESPONSE_CACHE_TTL_SECONDS)
# Prazo total da coleta: o timeout do requests vale por operação de socket, não pela
# requisição inteira; este prazo garante a resposta em ~10 s mesmo com fonte lenta.
COLLECT_DEADLINE_SECONDS = http.HTTP_TIMEOUT_SECONDS + 1.5
MAX_OUTSIDE_ARTICLES = 10

_response_cache = http.TTLCache(max_entries=256)
_executor = ThreadPoolExecutor(max_workers=12, thread_name_prefix="news-source")


class NewsUnavailableError(Exception):
    """Nenhuma fonte respondeu (a rota devolve 502 com o status de cada fonte)."""

    def __init__(self, sources: list[SourceStatus]) -> None:
        super().__init__("Nenhuma fonte de notícias respondeu")
        self.sources = sources


@dataclass(frozen=True)
class _Snapshot:
    location: NewsLocation
    generated_at: datetime
    crop: Optional[NewsCrop]
    articles: list[NewsArticle]  # já ordenados, antes do corte em `limit`
    results: list[SourceResult]  # sem os itens, só o status de cada fonte


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def clear_caches() -> None:
    _response_cache.clear()
    http.feed_cache.clear()


def enabled_sources() -> list[Source]:
    raw = os.getenv("NEWS_ENABLED_SOURCES", "")
    wanted = {s.strip() for s in raw.split(",") if s.strip()}
    if not wanted:
        return list(SOURCES.values())
    unknown = wanted - SOURCES.keys()
    if unknown:
        logger.warning("NEWS_ENABLED_SOURCES com fontes desconhecidas ignoradas: %s", sorted(unknown))
    return [source for source_id, source in SOURCES.items() if source_id in wanted]


def get_harvest_news(
    city: str,
    uf: Optional[str] = None,
    days: int = 30,
    limit: int = 10,
    crop: Optional[str] = None,
) -> NewsResponse:
    """Notícias para `city`/`uf`; com `crop` (classe do modelo), busca também por essa cultura.

    A ordem é: cultura na região, cultura em outras regiões, demais notícias de colheita da região.

    Levanta CityNotFoundError / ClimateProviderError (geocodificação) e
    NewsUnavailableError (todas as fontes falharam).
    """
    profile = get_crop(crop)
    cache_key = (normalize(" ".join(city.split())), uf or "", days, profile.id if profile else "")
    snapshot = _response_cache.get(cache_key)
    if snapshot is not None:
        return _to_response(snapshot, limit, cached=True)

    location = _resolve_location(city, uf)
    results = _collect(location, profile, days)
    if not any(r.ok for r in results):
        raise NewsUnavailableError([_status(r, kept=0, response_cached=False) for r in results])

    now = _utcnow()
    location_matcher = LocationMatcher(location)
    crop_matcher = CropMatcher(profile) if profile else None
    scored: list[ScoredItem] = []
    for result in results:
        source = SOURCES[result.source]
        for item in result.items:
            if not within_window(item.published_at, now, days):
                continue
            entry = score_item(
                item,
                location=location_matcher,
                location_filtered=source.location_filtered,
                now=now,
                crop=crop_matcher,
                agro_source=source.agro,
            )
            if entry:
                scored.append(entry)

    snapshot = _Snapshot(
        location=NewsLocation(city=location.city, state=location.state, uf=location.uf),
        generated_at=now.replace(microsecond=0),
        crop=NewsCrop(id=profile.id, name=profile.name, terms=list(profile.terms)) if profile else None,
        articles=[_to_article(s) for s in _cap_outside(rank(deduplicate(scored)))],
        results=[replace(r, items=[]) for r in results],
    )
    ttl = RESPONSE_CACHE_TTL_SECONDS if all(r.ok for r in results) else PARTIAL_RESPONSE_TTL_SECONDS
    _response_cache.set(cache_key, snapshot, ttl)
    return _to_response(snapshot, limit, cached=False)


def _cap_outside(ranked: list[ScoredItem]) -> list[ScoredItem]:
    """Limita a cultura em outras regiões, para ela não tirar da lista as notícias da região."""
    kept, outside = [], 0
    for scored in ranked:
        if scored.location_match == "outside":
            outside += 1
            if outside > MAX_OUTSIDE_ARTICLES:
                continue
        kept.append(scored)
    return kept


def _resolve_location(city: str, uf: Optional[str]) -> Location:
    coords = get_coordinates(city, state=uf)
    resolved_uf = coords.get("uf") or uf
    state_name = (BR_STATES.get(resolved_uf or "") or {}).get("name") or coords.get("state")
    return Location(city=coords.get("city") or city, state=state_name, uf=resolved_uf)


def _collect(location: Location, crop: Optional[CropProfile], days: int) -> list[SourceResult]:
    futures = [
        (source, _executor.submit(fetch_source, source, location, crop, days))
        for source in enabled_sources()
    ]
    wait([future for _, future in futures], timeout=COLLECT_DEADLINE_SECONDS)
    results: list[SourceResult] = []
    for source, future in futures:
        if not future.done():
            future.cancel()
            results.append(SourceResult(source.id, ok=False, error=f"timeout após {http.HTTP_TIMEOUT_SECONDS}s"))
            continue
        try:
            results.append(future.result())
        except Exception:  # um parser quebrado não pode derrubar a rota inteira
            logger.exception("Falha inesperada na fonte %s", source.id)
            results.append(SourceResult(source.id, ok=False, error="erro inesperado ao processar o feed"))
    return results


def _to_article(scored: ScoredItem) -> NewsArticle:
    item = scored.item
    return NewsArticle(
        id=article_id(item.url),
        title=item.title,
        summary=item.summary,
        url=item.url,
        source_name=item.source_name,
        source_feed=item.source_feed,
        published_at=item.published_at,
        image_url=item.image_url,
        location_match=scored.location_match,
        matched_keywords=scored.matched_keywords,
        crop_match=scored.crop_match,
        relevance_score=scored.relevance_score,
    )


def _status(result: SourceResult, kept: int, response_cached: bool) -> SourceStatus:
    return SourceStatus(
        source=result.source,
        ok=result.ok,
        items_fetched=result.items_fetched,
        items_kept=kept,
        cached=result.cached or (response_cached and result.ok),
        error=result.error,
    )


def _to_response(snapshot: _Snapshot, limit: int, cached: bool) -> NewsResponse:
    articles = snapshot.articles[:limit]
    kept = Counter(article.source_feed for article in articles)
    return NewsResponse(
        location=snapshot.location,
        generated_at=snapshot.generated_at,
        cached=cached,
        total=len(articles),
        crop=snapshot.crop,
        articles=articles,
        sources=[_status(r, kept=kept[r.source], response_cached=cached) for r in snapshot.results],
    )
