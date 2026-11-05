"""Relevância das notícias: tema, localidade, recência e cultura recomendada (SPEC §5.4).

- Tema: comparado no texto **normalizado** (minúsculas, sem acento), palavra inteira.
- Localidade: comparada no texto **original** (caixa e acento), palavra inteira, para
  "para" não virar Pará, "se" não virar SE e "sorriso" não virar Sorriso (MT).
- Cultura (`crop`): notícia que cita a cultura recomendada vem primeiro. Em fonte
  especializada ela dispensa o corte de tema e pode vir de fora da região (`outside`).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import urlsplit

from services.br_states import BR_STATES
from services.news.crops import CropProfile
from services.news.sources import Location, RawItem

STRONG_TERMS = ("colheita", "safra", "plantio", "semeadura", "quebra de safra")
WEAK_TERMS = (
    "lavoura", "produtividade", "sacas", "hectares", "estiagem", "geada", "conab",
    "soja", "milho", "cana", "café", "trigo", "algodão", "feijão", "arroz", "laranja",
    "amendoim", "mandioca",
)
STRONG_WEIGHT = 3
WEAK_WEIGHT = 1
HARVEST_CAP = 6
HARVEST_CUTOFF = 3
LOCATION_POINTS = {"city": 5, "state": 3, "inferred": 1, "outside": 0}
LOCATION_RANK = {"city": 3, "state": 2, "inferred": 1, "outside": 0}
CROP_BONUS = 3
# Sinais de problema na lavoura. Palavra-chave não entende negação ("sem geada"): servem só
# para avisar, com o link da notícia, nunca para mudar a ordem das culturas.
RISK_TERMS = ("geada", "estiagem", "seca", "granizo", "enchente", "praga", "doença", "quebra de safra")


def normalize(text: str) -> str:
    """Minúsculas e sem acentos (NFKD)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _term_regex(term: str) -> re.Pattern[str]:
    # Palavra inteira com plural opcional: "safras" casa com "safra", "canal" não casa com "cana".
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(rf"(?<!\w){body}s?(?!\w)")


_HARVEST_PATTERNS = [
    (term, STRONG_WEIGHT if term in STRONG_TERMS else WEAK_WEIGHT, _term_regex(normalize(term)))
    for term in STRONG_TERMS + WEAK_TERMS
]


_RISK_PATTERNS = [(term, _term_regex(normalize(term))) for term in RISK_TERMS]


def risk_terms(text: str) -> list[str]:
    """Termos de risco citados no texto."""
    normalized = normalize(text)
    return [term for term, pattern in _RISK_PATTERNS if pattern.search(normalized)]


def harvest_score(text: str) -> tuple[int, list[str]]:
    """(pontuação de tema limitada a HARVEST_CAP, termos encontrados)."""
    normalized = normalize(text)
    score, matched = 0, []
    for term, weight, pattern in _HARVEST_PATTERNS:
        if pattern.search(normalized):
            score += weight
            matched.append(term)
    return min(score, HARVEST_CAP), matched


def _exact_words(variants: Iterable[str], not_followed_by: Iterable[str] = ()) -> Optional[re.Pattern[str]]:
    alternatives = "|".join(re.escape(v) for v in dict.fromkeys(variants) if v)
    if not alternatives:
        return None
    lookaheads = "".join(rf"(?!\s+{re.escape(suffix)}(?!\w))" for suffix in not_followed_by)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w){lookaheads}")


def _state_pattern(name: str) -> Optional[re.Pattern[str]]:
    # "Mato Grosso" não pode casar dentro de "Mato Grosso do Sul": vale para qualquer
    # nome de estado que seja prefixo de outro.
    longer = [other[len(name):].strip() for other in _state_names() if other.startswith(name + " ")]
    return _exact_words([name, name.upper()], not_followed_by=longer)


def _state_names() -> list[str]:
    return [info["name"] for info in BR_STATES.values()]


class LocationMatcher:
    def __init__(self, location: Location) -> None:
        self.location = location
        city = unicodedata.normalize("NFC", location.city or "").strip()
        state_name = (BR_STATES.get(location.uf or "") or {}).get("name") or location.state or ""
        self._city = _exact_words([city, city.upper()]) if city else None
        self._state = _state_pattern(state_name) if state_name else None
        # UF só em maiúsculas, como token isolado: SP, (SP), /SP, - SP.
        self._uf = _exact_words([location.uf]) if location.uf else None

    def match(self, text: str, location_filtered: bool) -> Optional[str]:
        text = unicodedata.normalize("NFC", text)
        if self._city and self._city.search(text):
            return "city"
        if (self._state and self._state.search(text)) or (self._uf and self._uf.search(text)):
            return "state"
        return "inferred" if location_filtered else None


class CropMatcher:
    """Termos da cultura casados em minúsculas **com** acento (ver services/news/crops.py)."""

    def __init__(self, crop: CropProfile) -> None:
        self.crop = crop
        self._patterns = [(term, _term_regex(term)) for term in crop.terms]

    def match(self, text: str) -> list[str]:
        lowered = unicodedata.normalize("NFC", text).lower()
        return [term for term, pattern in self._patterns if pattern.search(lowered)]


def recency_score(published_at: Optional[datetime], now: datetime) -> int:
    if published_at is None:
        return 0
    age = now - published_at
    if age <= timedelta(days=7):
        return 2
    if age <= timedelta(days=30):
        return 1
    return 0


def within_window(published_at: Optional[datetime], now: datetime, days: int) -> bool:
    # Itens sem data passam pelo filtro (recência zero, SPEC §5.3).
    return published_at is None or published_at >= now - timedelta(days=days)


@dataclass
class ScoredItem:
    item: RawItem
    location_match: str
    matched_keywords: list[str]
    harvest_score: int
    location_score: int
    recency_score: int
    crop_terms: list[str]
    relevance_score: int

    @property
    def crop_match(self) -> bool:
        return bool(self.crop_terms)

    @property
    def tier(self) -> int:
        """2 = cultura na região · 1 = cultura em outras regiões · 0 = só a região."""
        if not self.crop_match:
            return 0
        return 1 if self.location_match == "outside" else 2


def score_item(
    item: RawItem,
    *,
    location: LocationMatcher,
    location_filtered: bool,
    now: datetime,
    crop: Optional[CropMatcher] = None,
    agro_source: bool = False,
) -> Optional[ScoredItem]:
    """Pontua o item; devolve None se ele não passa no corte.

    Corte: tema ≥ 3 **e** localidade. Em fonte especializada (`agro_source`), citar a
    cultura pedida substitui os dois; sem menção ao local, o item fica como "outside".
    """
    text = f"{item.title} {item.summary or ''}"
    theme, keywords = harvest_score(text)
    crop_terms = crop.match(text) if crop else []
    crop_relevant = bool(crop_terms) and agro_source
    if theme < HARVEST_CUTOFF and not crop_relevant:
        return None
    match = location.match(text, location_filtered)
    if match is None:
        if not crop_relevant:
            return None
        match = "outside"
    recency = recency_score(item.published_at, now)
    known = {normalize(k) for k in keywords}
    keywords += [t for t in crop_terms if normalize(t) not in known]
    total = theme + LOCATION_POINTS[match] + recency + (CROP_BONUS if crop_terms else 0)
    return ScoredItem(
        item=item,
        location_match=match,
        matched_keywords=keywords,
        harvest_score=theme,
        location_score=LOCATION_POINTS[match],
        recency_score=recency,
        crop_terms=crop_terms,
        relevance_score=total,
    )


def canonical_url(url: str) -> str:
    """Host + caminho, sem esquema, query string, fragmento ou barra final."""
    parts = urlsplit(url)
    return f"{parts.netloc.lower()}{parts.path.rstrip('/') or '/'}"


def title_key(title: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", normalize(title)).split())


def article_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def _timestamp(value: Optional[datetime]) -> float:
    return value.timestamp() if value else float("-inf")


def deduplicate(items: Iterable[ScoredItem]) -> list[ScoredItem]:
    """Remove duplicatas por URL canônica e por título normalizado.

    Entre duplicatas fica a que tem imagem e, depois, o maior location_match.
    """
    preferred = sorted(
        items,
        key=lambda s: (
            s.item.image_url is not None,
            LOCATION_RANK[s.location_match],
            s.relevance_score,
            _timestamp(s.item.published_at),
        ),
        reverse=True,
    )
    seen: set[tuple[str, str]] = set()
    kept: list[ScoredItem] = []
    for scored in preferred:
        keys = {("url", canonical_url(scored.item.url)), ("title", title_key(scored.item.title))}
        if keys & seen:
            continue
        seen |= keys
        kept.append(scored)
    return kept


def rank(items: Iterable[ScoredItem]) -> list[ScoredItem]:
    """Cultura + região primeiro; dentro de cada faixa, relevance_score e published_at desc."""
    return sorted(items, key=lambda s: (s.tier, s.relevance_score, _timestamp(s.item.published_at)), reverse=True)
