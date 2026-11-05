"""Report da recomendação cruzada: junta a ordem do modelo com a leitura das notícias.

Os textos daqui são montados só com dados já calculados (probabilidades e contagens do classificador).
Quando a IA responde, a conclusão pode ser trocada pela dela (services/llm_reader.py); estes textos
continuam sendo a reserva e o texto-base que ela recebe.
"""
from __future__ import annotations

from typing import Optional, Sequence

from schemas.cross_schema import ClassifiedArticle, CropOutlook, CrossCandidate, CrossReport

NEWS_DAYS = 30
MAX_SIGNALS = 3

CAVEAT = (
    "Leitura automática das manchetes, por palavras-chave. O modelo avalia solo e clima; "
    "as notícias falam de mercado e safra. Confira as notícias antes de decidir."
)
AI_CAVEAT = (
    "Leitura feita por IA ({model}), que pode errar. O modelo de recomendação avalia solo e clima; "
    "as notícias falam de mercado e safra. Confira as notícias antes de decidir."
)


def percent(probability: float) -> str:
    return f"{probability:.0f}%"


def news_count(count: int) -> str:
    return "1 notícia" if count == 1 else f"{count} notícias"


def join_names(names: Sequence[str]) -> str:
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} e {names[-1]}"


def _label(candidate: CrossCandidate) -> str:
    return f"{candidate.name} ({percent(candidate.probability)})"


def _count(articles: list[ClassifiedArticle], sentiment: str) -> int:
    return sum(article.sentiment == sentiment for article in articles)


def _has_signal(articles: list[ClassifiedArticle]) -> bool:
    return any(article.sentiment != "neutral" for article in articles)


def _signal_list(articles: list[ClassifiedArticle], sentiment: str) -> str:
    signals = dict.fromkeys(signal for a in articles if a.sentiment == sentiment for signal in a.signals)
    return ", ".join(list(signals)[:MAX_SIGNALS])


def _outlook_sentiment(articles: list[ClassifiedArticle]) -> str:
    positive, negative = _count(articles, "positive"), _count(articles, "negative")
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "mixed" if _has_signal(articles) else "neutral"


def _outlook_text(sentiment: str, articles: list[ClassifiedArticle], where: str) -> str:
    total = len(articles)
    positive, negative = _count(articles, "positive"), _count(articles, "negative")
    if sentiment in ("positive", "negative"):
        label, count = ("favoráveis", positive) if sentiment == "positive" else ("desfavoráveis", negative)
        signals = _signal_list(articles, sentiment)
        return f"Notícias {label} {where}: {count} de {total}" + (f" ({signals})." if signals else ".")
    if sentiment == "mixed":
        return f"Notícias divididas {where}: {positive} a favor e {negative} contra, de {total}."
    return f"{news_count(total)} {where}, sem sinal claro de alta ou queda."


def build_outlook(articles: list[ClassifiedArticle], *, generic: bool = False) -> CropOutlook:
    """Lê a região primeiro. As outras regiões valem quando a região não traz sinal claro."""
    regional = [article for article in articles if article.regional]
    others = [article for article in articles if not article.regional]
    if not articles:
        return CropOutlook(
            sentiment="no_news",
            positive=0,
            negative=0,
            neutral=0,
            text=f"Nenhuma notícia sobre a cultura nos últimos {NEWS_DAYS} dias.",
            articles=[],
        )

    if regional and (_has_signal(regional) or not _has_signal(others)):
        scope, in_scope, where = "region", regional, "na região"
    else:
        scope, in_scope, where = "other_regions", others, "em outras regiões"

    sentiment = _outlook_sentiment(in_scope)
    text = _outlook_text(sentiment, in_scope, where)
    positive, negative = _count(in_scope, "positive"), _count(in_scope, "negative")
    return CropOutlook(
        sentiment=sentiment,
        scope=scope,
        positive=positive,
        negative=negative,
        neutral=len(in_scope) - positive - negative,
        text=f"{text} Falam de feijão em geral, não desta variedade." if generic else text,
        articles=[*regional, *others],
    )


def unavailable_outlook() -> CropOutlook:
    return CropOutlook(
        sentiment="unavailable",
        positive=0,
        negative=0,
        neutral=0,
        text="Não foi possível consultar as notícias agora.",
        articles=[],
    )


def _opening(first: CrossCandidate) -> str:
    return {
        "positive": f"{_label(first)} lidera no modelo, com notícias favoráveis só em outras regiões.",
        "negative": f"{_label(first)} lidera no modelo, mas as notícias são desfavoráveis.",
        "mixed": f"{_label(first)} lidera no modelo, com notícias divididas.",
        "no_news": f"{_label(first)} lidera no modelo, sem notícias recentes.",
    }.get(first.outlook.sentiment, f"{_label(first)} lidera no modelo, sem sinal claro nas notícias.")


def _conclusion(by_model: list[CrossCandidate], leader: CrossCandidate) -> str:
    first = by_model[0]
    if any(candidate.outlook.sentiment == "unavailable" for candidate in by_model):
        return (
            "As notícias não responderam para todas as culturas e a leitura está incompleta: "
            f"vale o modelo, com {_label(first)} à frente."
        )
    if not {candidate.outlook.sentiment for candidate in by_model} & {"positive", "negative", "mixed"}:
        return f"As notícias não mostram sinal claro de alta ou queda: vale o modelo, com {_label(first)} à frente."
    if leader.crop != first.crop:
        return (
            f"{_opening(first)} {_label(leader)}, com probabilidade próxima, "
            "passou à frente pelas notícias da região."
        )
    if first.outlook.sentiment == "positive":
        return (
            f"{_label(first)} reúne a maior probabilidade do modelo e notícias favoráveis: "
            "é a indicação mais sustentada."
        )

    if len(by_model) == 1:
        return f"{_opening(first)} É a única com probabilidade relevante no modelo."

    favorable = next((c for c in by_model[1:] if c.outlook.sentiment == "positive"), None)
    if favorable:
        return (
            f"{_opening(first)} {_label(favorable)} tem notícias favoráveis, mas o modelo a considera menos "
            "adequada ao solo e ao clima: avalie antes de trocar."
        )
    unfavorable = [c.name for c in by_model[1:] if c.outlook.sentiment == "negative"]
    if unfavorable:
        verb = "tem" if len(unfavorable) == 1 else "têm"
        return (
            f"{_opening(first)} {join_names(unfavorable)} {verb} notícias desfavoráveis: "
            "a ordem do modelo se mantém."
        )
    return f"{_opening(first)} Nenhuma outra tem notícias favoráveis: a ordem do modelo se mantém."


def caveat_for(model: Optional[str]) -> str:
    return AI_CAVEAT.format(model=model) if model else CAVEAT


def build_report(
    candidates: list[CrossCandidate],
    leader: CrossCandidate,
    *,
    model: Optional[str] = None,
) -> CrossReport:
    """`model`: o modelo de IA que classificou notícias desta consulta, se algum classificou."""
    by_model = sorted(candidates, key=lambda candidate: candidate.model_rank)
    return CrossReport(conclusion=_conclusion(by_model, leader), caveat=caveat_for(model), model=model)
