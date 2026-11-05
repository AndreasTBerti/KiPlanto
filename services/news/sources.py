"""Adaptadores das fontes de notícias: feeds RSS e busca por cultura (SPEC §4.1).

Cada fonte vira um `Source`; `fetch_source(source, location, crop, days)` baixa o feed
(ou, em fontes com busca, consulta pela cultura), normaliza os itens para `RawItem` e
devolve um `SourceResult` (nunca levanta exceção de rede).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode, urlsplit

import feedparser
from bs4 import BeautifulSoup

from services.br_states import BR_STATES
from services.news import http
from services.news.crops import CropProfile

SUMMARY_MAX_CHARS = 500
SEARCH_RESULTS = 50
PUBLIEDITORIAL_MARKER = "/especial-publicitario/"
_WORDPRESS_FOOTER_RE = re.compile(r"\s*O post .{0,400}? apareceu primeiro em .{0,80}?\.?\s*$", re.S)
_IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)(?:$|\?)", re.I)


@dataclass(frozen=True)
class Location:
    city: str
    state: Optional[str] = None
    uf: Optional[str] = None


@dataclass
class RawItem:
    title: str
    url: str
    source_name: str
    source_feed: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None


@dataclass
class SourceResult:
    source: str
    ok: bool
    items: list[RawItem] = field(default_factory=list)
    items_fetched: int = 0
    cached: bool = False
    error: Optional[str] = None


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url_template: str
    # Feed já filtrado pela localidade na origem (g1 estadual): itens sem menção
    # explícita ao local entram como location_match="inferred" (SPEC §5.4).
    location_filtered: bool = False
    # g1 traz o lead em <atom:subtitle> e a matéria inteira em <description>:
    # usar o subtitle evita reproduzir o corpo da matéria (SPEC §8).
    prefer_subtitle: bool = False
    # Veículo especializado em agro: citar a cultura já basta como tema. Em feed de
    # notícias gerais (g1 estadual), "manga" ou "coco" podem não ser sobre lavoura.
    agro: bool = True
    # API REST do WordPress: com cultura pedida, consulta por ela em vez de ler o feed.
    # O termo vem de CROPS, nunca do cliente (SPEC §5.10). robots.txt verificado em 2026-11-04.
    search_url: Optional[str] = None

    def feed_url(self, location: Location) -> Optional[str]:
        if "{g1_feed}" not in self.url_template:
            return self.url_template
        state = BR_STATES.get(location.uf or "")
        if not state:
            return None
        return self.url_template.format(g1_feed=state["g1_feed"])


SOURCES: dict[str, Source] = {
    s.id: s
    for s in (
        Source("g1_estadual", "g1", "https://g1.globo.com/rss/g1/{g1_feed}/",
               location_filtered=True, prefer_subtitle=True, agro=False),
        Source("g1_agro", "g1", "https://g1.globo.com/rss/g1/economia/agronegocios/", prefer_subtitle=True),
        Source("canal_rural", "Canal Rural", "https://www.canalrural.com.br/feed/"),
        Source("portal_agronegocio", "Portal do Agronegócio", "https://www.portaldoagronegocio.com.br/feed"),
        Source("globo_rural", "Globo Rural", "https://globorural.globo.com/rss/globorural/", prefer_subtitle=True),
        Source("compre_rural", "Compre Rural", "https://www.comprerural.com/feed/",
               search_url="https://www.comprerural.com/wp-json/wp/v2/posts"),
    )
}


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def safe_http_url(value: Any) -> Optional[str]:
    """Aceita só URLs absolutas http(s); descarta javascript:, data: etc. (SPEC §5.10)."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return value


def html_to_text(html: Optional[str]) -> str:
    """HTML do feed → texto puro, sem legenda de foto (<figure>/<figcaption>) nem rodapé do WordPress."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["figure", "figcaption", "img", "script", "style", "iframe"]):
        tag.decompose()
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text.startswith("O post ") and "apareceu primeiro em" in text:
            p.decompose()
    text = soup.get_text(" ", strip=True)
    text = _WORDPRESS_FOOTER_RE.sub("", text)
    return " ".join(text.split())


def truncate_words(text: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    """Corta no limite de palavra; o resultado (com reticências) tem no máximo `max_chars`."""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-–—") + "…"


def _published_at(entry: Any) -> Optional[datetime]:
    # feedparser já converte para UTC em *_parsed.
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _image_url(entry: Any) -> Optional[str]:
    candidates: list[Any] = []
    for media in entry.get("media_content") or []:
        if media.get("medium") in (None, "image") or _IMAGE_EXT_RE.search(media.get("url", "")):
            candidates.append(media.get("url"))
    candidates += [m.get("url") for m in entry.get("media_thumbnail") or []]
    candidates += [
        link.get("href") for link in entry.get("links") or []
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image/")
    ]
    # Portal do Agronegócio usa <image><url>…</url></image> dentro do <item>;
    # o feedparser expõe isso como entry["href"].
    image = entry.get("image")
    if isinstance(image, dict):
        candidates.append(image.get("href") or image.get("url"))
    if _IMAGE_EXT_RE.search(str(entry.get("href", ""))):
        candidates.append(entry.get("href"))
    html = entry.get("summary") or ""
    if "<img" in html:
        img = BeautifulSoup(html, "html.parser").find("img", src=True)
        if img:
            candidates.append(img["src"])
    for candidate in candidates:
        url = safe_http_url(candidate)
        if url:
            return url
    return None


def _summary(entry: Any, source: Source) -> Optional[str]:
    text = ""
    if source.prefer_subtitle:
        text = html_to_text(entry.get("subtitle"))
    if not text:
        text = html_to_text(entry.get("summary"))
    return truncate_words(text) if text else None


def entry_to_item(entry: Any, source: Source) -> Optional[RawItem]:
    title = " ".join(html_to_text(entry.get("title")).split())
    url = safe_http_url(entry.get("link"))
    if not title or not url or PUBLIEDITORIAL_MARKER in url:
        return None
    return RawItem(
        title=title,
        url=url,
        source_name=source.name,
        source_feed=source.id,
        summary=_summary(entry, source),
        published_at=_published_at(entry),
        image_url=_image_url(entry),
    )


def parse_feed(content: bytes, source: Source) -> tuple[list[RawItem], int]:
    """Devolve (itens válidos, total de entradas no feed)."""
    parsed = feedparser.parse(content)
    if parsed.get("bozo") and not parsed.entries:
        raise http.FetchError("feed inválido")
    items = [item for item in (entry_to_item(e, source) for e in parsed.entries) if item]
    return items, len(parsed.entries)


def search_url(source: Source, crop: CropProfile, days: int) -> str:
    # Só a data no `after`: a URL fica estável durante o dia e o cache por URL funciona.
    after = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    params = {
        "search": crop.terms[0],
        "after": f"{after}T00:00:00",
        "orderby": "relevance",
        "per_page": SEARCH_RESULTS,
        "_fields": "date_gmt,link,title,excerpt,yoast_head_json.og_image",
    }
    return f"{source.search_url}?{urlencode(params)}"


def _rendered(post: dict, key: str) -> Optional[str]:
    value = post.get(key)
    return value.get("rendered") if isinstance(value, dict) else None


def _post_date(post: dict) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(post["date_gmt"]).replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return None


def _post_image(post: dict) -> Optional[str]:
    images = (post.get("yoast_head_json") or {}).get("og_image") or []
    return safe_http_url(images[0].get("url")) if images else None


def post_to_item(post: dict, source: Source) -> Optional[RawItem]:
    title = html_to_text(_rendered(post, "title"))
    url = safe_http_url(post.get("link"))
    if not title or not url:
        return None
    summary = html_to_text(_rendered(post, "excerpt"))
    return RawItem(
        title=title,
        url=url,
        source_name=source.name,
        source_feed=source.id,
        summary=truncate_words(summary) if summary else None,
        published_at=_post_date(post),
        image_url=_post_image(post),
    )


def parse_search(content: bytes, source: Source) -> tuple[list[RawItem], int]:
    """Devolve (itens válidos, total de posts). Busca sem resultado é válida, ao contrário de feed vazio."""
    try:
        posts = json.loads(content)
    except ValueError as exc:
        raise http.FetchError("resposta de busca inválida") from exc
    if not isinstance(posts, list):
        raise http.FetchError("resposta de busca inválida")
    items = [post_to_item(post, source) for post in posts if isinstance(post, dict)]
    return [item for item in items if item], len(posts)


def _fetch_search(source: Source, crop: CropProfile, days: int) -> SourceResult:
    try:
        fetched = http.fetch(search_url(source, crop, days))
        items, total = parse_search(fetched.content, source)
    except http.FetchError as exc:
        return SourceResult(source=source.id, ok=False, error=str(exc))
    return SourceResult(source=source.id, ok=True, items=items, items_fetched=total, cached=fetched.cached)


def fetch_source(
    source: Source,
    location: Location,
    crop: Optional[CropProfile] = None,
    days: int = 30,
) -> SourceResult:
    if crop and source.search_url:
        return _fetch_search(source, crop, days)
    url = source.feed_url(location)
    if url is None:
        return SourceResult(source=source.id, ok=False, error="estado não identificado para o feed estadual")
    try:
        fetched = http.fetch(url)
        items, total = parse_feed(fetched.content, source)
    except http.FetchError as exc:
        return SourceResult(source=source.id, ok=False, error=str(exc))
    if total == 0:
        # O g1 responde 200 com 0 itens para feed inexistente (SPEC §4.1).
        return SourceResult(source=source.id, ok=False, cached=fetched.cached, error="feed vazio ou inexistente")
    return SourceResult(source=source.id, ok=True, items=items, items_fetched=total, cached=fetched.cached)
