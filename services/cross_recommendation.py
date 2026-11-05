"""Recomendação cruzada: o modelo define as 3 candidatas, as notícias desempatam as mais próximas.

As candidatas são sempre as 3 primeiras do modelo, as mesmas da tela. Uma IA barata
(services/llm_reader.py) separa o que é mesmo notícia de cada uma e diz se é favorável; o que ela não
responder fica com as regras locais (services/news/classifier.py). O report
(services/cross_report.py) junta essa leitura com a predição.

Só muda a ordem quem está perto da primeira: uma cultura de 5% não passa uma de 44% por causa de
notícia. As notícias nunca indicam uma cultura fora das candidatas. Não há nota ponderada: os pesos
seriam arbitrários e culturas muito noticiadas ganhariam em qualquer solo. Por isso conta só *ter ou
não* notícia da região sem saldo desfavorável, e não quantas. Não ter notícia não rebaixa a cultura;
se a busca falhou para alguma candidata, a comparação seria injusta e vale o modelo.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Mapping, Optional

from schemas.cross_schema import CitedCrop, ClassifiedArticle, CrossAlert, CrossCandidate, CrossRecommendationOutput
from schemas.news_schema import NewsArticle, NewsResponse
from services.climate_data_service import ClimateProviderError
from services.cross_report import (
    NEWS_DAYS,
    build_outlook,
    build_report,
    caveat_for,
    join_names,
    news_count,
    percent,
    unavailable_outlook,
)
from services.llm_reader import NewsItem, classify_news, write_conclusion
from services.news.classifier import Classification, classify_article
from services.news.crops import CROPS
from services.news.relevance import CropMatcher, risk_terms
from services.news.service import NewsUnavailableError, get_harvest_news

Classifications = Mapping[tuple[str, str], Classification]

MIN_SHOWN = 1.0  # %: a tela também não mostra menos que isso (model/crop_model.py)
MIN_PROBABILITY = 10.0  # %: abaixo disso, a cultura não passa outra por causa de notícia
MAX_GAP = 10.0  # pontos percentuais até a primeira colocada para poder passar à frente
MAX_CANDIDATES = 3
MIN_CITATIONS = 2  # notícias da região para aparecer em `also_cited`
MAX_ALSO_CITED = 3
NEWS_LIMIT = 30
# Termo compartilhado por várias classes do modelo: não é evidência de nenhuma delas.
GENERIC_TERMS = frozenset({"feijão"})

# Cada busca de notícias já usa o pool de services/news/service.py; este só as dispara.
_pool = ThreadPoolExecutor(max_workers=MAX_CANDIDATES - 1, thread_name_prefix="cross-news")

_specific_matchers = {
    crop_id: CropMatcher(replace(profile, terms=specific))
    for crop_id, profile in CROPS.items()
    if (specific := tuple(term for term in profile.terms if term not in GENERIC_TERMS))
}


def select_candidates(probabilities: Mapping[str, float]) -> list[tuple[str, float]]:
    """As 3 primeiras do modelo. A primeira entra sempre; as demais, se a tela também as mostra."""
    first, *others = sorted(probabilities.items(), key=lambda entry: (-entry[1], entry[0]))
    return [first, *(entry for entry in others if entry[1] > MIN_SHOWN)][:MAX_CANDIDATES]


def _is_close(first_probability: float, probability: float) -> bool:
    return probability >= MIN_PROBABILITY and first_probability - probability <= MAX_GAP


def _name(crop: str) -> str:
    profile = CROPS.get(crop)
    return profile.name if profile else crop


def _text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary or ''}"


def _cites_specifically(crop: str, article: NewsArticle) -> bool:
    matcher = _specific_matchers.get(crop)
    return bool(matcher and matcher.match(_text(article)))


def _classify(crop: str, article: NewsArticle, by_llm: Classifications) -> Classification:
    found = by_llm.get((crop, article.id))
    if found is not None:
        return found
    profile = CROPS.get(crop)
    return classify_article(profile, article.title, article.summary) if profile else Classification(False, "neutral")


def _classified(article: NewsArticle, classification: Classification) -> ClassifiedArticle:
    return ClassifiedArticle(
        article_id=article.id,
        title=article.title,
        regional=article.location_match != "outside",
        sentiment=classification.sentiment,
        signals=classification.signals,
        classified_by=classification.source,
    )


def _sentiment_is_negative(articles: list[ClassifiedArticle]) -> bool:
    return sum(a.sentiment == "negative" for a in articles) > sum(a.sentiment == "positive" for a in articles)


def _candidate(
    crop: str,
    probability: float,
    rank: int,
    news: Optional[NewsResponse],
    by_llm: Classifications,
) -> tuple[CrossCandidate, bool]:
    """(candidata, tem notícia específica da região sem saldo desfavorável)."""
    if news is None:
        status, summary, regional, alerts, has_evidence = "unavailable", "Notícias indisponíveis agora.", [], [], False
        outlook = unavailable_outlook()
    else:
        classified = {
            article.id: _classified(article, classification)
            for article in news.articles
            if article.crop_match and (classification := _classify(crop, article, by_llm)).about_crop
        }
        regional = [a for a in news.articles if a.id in classified and a.location_match != "outside"]
        specific = [a for a in regional if _cites_specifically(crop, a)]
        has_evidence = bool(specific) and not _sentiment_is_negative([classified[a.id] for a in specific])
        about_crop = [a for a in news.articles if a.id in classified]
        generic = bool(about_crop) and not any(_cites_specifically(crop, a) for a in about_crop)
        outlook = build_outlook(list(classified.values()), generic=generic)
        alerts = [
            CrossAlert(article_id=a.id, title=a.title, terms=terms)
            for a in specific
            if (terms := risk_terms(_text(a)))
        ]
        if alerts:
            terms = sorted({term for alert in alerts for term in alert.terms})
            status, summary = "alert", f"Indicada, com alerta na região ({', '.join(terms)}). Confira a notícia."
        elif specific:
            status, summary = "news", f"Indicada, com movimento na região: {news_count(len(specific))}."
        elif regional:
            status = "generic_news"
            summary = f"{news_count(len(regional))} da região sobre o termo geral, sem efeito na ordem."
        else:
            status, summary = "no_news", "Indicada, sem notícias recentes na região."

    candidate = CrossCandidate(
        crop=crop,
        name=_name(crop),
        probability=probability,
        model_rank=rank,
        regional_news=len(regional),
        status=status,
        summary=summary,
        alerts=alerts,
        outlook=outlook,
        news=news,
    )
    return candidate, has_evidence


def _also_cited(
    probabilities: Mapping[str, float],
    candidates: list[CrossCandidate],
    news_by_crop: Mapping[str, Optional[NewsResponse]],
) -> list[CitedCrop]:
    articles = {
        article.id: article
        for news in news_by_crop.values()
        if news is not None
        for article in news.articles
        if article.location_match != "outside"
    }
    excluded = {candidate.crop for candidate in candidates}
    cited = []
    for crop in _specific_matchers:
        if crop in excluded:
            continue
        mentions = sum(_cites_specifically(crop, article) for article in articles.values())
        if mentions >= MIN_CITATIONS:
            cited.append(
                CitedCrop(crop=crop, name=_name(crop), mentions=mentions, probability=probabilities.get(crop, 0.0))
            )
    return sorted(cited, key=lambda c: (-c.mentions, -c.probability, c.crop))[:MAX_ALSO_CITED]


def _explanation(
    by_model: list[CrossCandidate],
    leader: CrossCandidate,
    any_unavailable: bool,
    leader_has_evidence: bool,
) -> str:
    first, *others = by_model
    model_says = f"O modelo indicou {first.name} ({percent(first.probability)})"
    if any_unavailable:
        return f"{model_says}. As notícias não responderam para todas as culturas: vale a ordem do modelo."
    if leader.crop != first.crop:
        return (
            f"{model_says}; {leader.name} ({percent(leader.probability)}) passou à frente "
            f"por ter {news_count(leader.regional_news)} na região."
        )
    if not others:
        return f"{model_says}, sem outra cultura com probabilidade relevante."
    if leader_has_evidence:
        return f"{model_says}, e ela também aparece nas notícias da região."
    if not any(_is_close(first.probability, other.probability) for other in others):
        names = join_names([f"{other.name} ({percent(other.probability)})" for other in others])
        return f"{model_says}, à frente de {names}."
    if first.regional_news:
        return f"{model_says}. As notícias da região não mudam a ordem."
    return f"{model_says}. Nenhuma cultura próxima tem notícias na região para desempatar."


def combine(
    probabilities: Mapping[str, float],
    news_by_crop: Mapping[str, Optional[NewsResponse]],
    by_llm: Optional[Classifications] = None,
) -> CrossRecommendationOutput:
    """Regra do cruzamento, sem rede: `news_by_crop` traz None para a busca que falhou.

    `by_llm` traz as classificações já feitas pela IA; o que faltar é classificado pelas regras.
    """
    by_llm = by_llm or {}
    selected = select_candidates(probabilities)
    built = [
        _candidate(crop, probability, rank, news_by_crop.get(crop), by_llm)
        for rank, (crop, probability) in enumerate(selected, start=1)
    ]
    by_model = [candidate for candidate, _ in built]
    first = by_model[0]
    any_unavailable = any(candidate.status == "unavailable" for candidate in by_model)
    if any_unavailable:
        ordered = built
    else:
        # sorted é estável: entre as que têm (ou não têm) notícias, fica a ordem do modelo.
        ordered = sorted(
            built,
            key=lambda entry: not (entry[1] and _is_close(first.probability, entry[0].probability)),
        )

    candidates = [candidate for candidate, _ in ordered]
    leader = candidates[0]
    return CrossRecommendationOutput(
        model_recommendation=first.crop,
        recommendation=leader.crop,
        changed=leader.crop != first.crop,
        explanation=_explanation(by_model, leader, any_unavailable, ordered[0][1]),
        report=build_report(candidates, leader, model=_model_used(by_llm, candidates)),
        candidates=candidates,
        also_cited=_also_cited(probabilities, candidates, news_by_crop),
    )


def _model_used(by_llm: Classifications, candidates: list[CrossCandidate]) -> Optional[str]:
    for candidate in candidates:
        for article in candidate.outlook.articles:
            found = by_llm.get((candidate.crop, article.article_id))
            if found is not None and found.model:
                return found.model
    return None


def _news_items(
    selected: list[tuple[str, float]],
    news_by_crop: Mapping[str, Optional[NewsResponse]],
) -> list[NewsItem]:
    """As notícias que citam cada candidata, na ordem de relevância da busca."""
    return [
        NewsItem(crop, article.id, article.title, article.summary)
        for crop, _ in selected
        if (news := news_by_crop.get(crop)) is not None
        for article in news.articles
        if article.crop_match
    ]


def _fetch_news(crop: str, city: str, uf: Optional[str]) -> Optional[NewsResponse]:
    try:
        return get_harvest_news(city, uf=uf, days=NEWS_DAYS, limit=NEWS_LIMIT, crop=crop)
    except (NewsUnavailableError, ClimateProviderError):
        return None


def cross_recommend(
    probabilities: Mapping[str, float],
    *,
    city: str,
    uf: Optional[str] = None,
) -> CrossRecommendationOutput:
    """Busca as notícias de cada candidata e cruza. CityNotFoundError sobe para a rota."""
    first, *others = [crop for crop, _ in select_candidates(probabilities)]
    # A primeira busca preenche o cache dos feeds, para as demais não baixarem os mesmos RSS
    # ao mesmo tempo: elas só acrescentam a busca da própria cultura.
    news_by_crop = {first: _fetch_news(first, city, uf)}
    results = _pool.map(lambda crop: _fetch_news(crop, city, uf), others)
    news_by_crop.update(zip(others, results, strict=True))

    # Sem chave ou com o modelo fora do ar, as duas chamadas abaixo não mudam nada: valem as regras.
    by_llm = classify_news(_news_items(select_candidates(probabilities), news_by_crop))
    result = combine(probabilities, news_by_crop, by_llm)
    written = write_conclusion(result.candidates, result.report.conclusion)
    if written is None:
        return result
    conclusion, model = written
    used = result.report.model or model
    report = result.report.model_copy(
        update={"conclusion": conclusion, "conclusion_by": "llm", "model": used, "caveat": caveat_for(used)}
    )
    return result.model_copy(update={"report": report})
