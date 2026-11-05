"""Classificador de notícias: a notícia é da cultura? E é boa ou ruim para quem a produz?

É baseado em regras (léxico em português), sem rede e sem chave de API: o mesmo texto dá sempre
o mesmo resultado, e `signals` mostra quais palavras decidiram. O sentimento é por cultura:
em "Soja sobe, milho cai", a soja é positiva e o milho é negativo. O título tem prioridade,
porque o resumo costuma trazer assuntos paralelos.

O ponto de vista é o do produtor: preço em alta é bom e custo em alta é ruim.
Regras não entendem ironia nem contexto longo: o resultado é uma leitura rápida, não um parecer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional

from services.news.crops import CROPS, CropProfile
from services.news.relevance import CropMatcher, normalize

POSITIVE = "positive"
NEGATIVE = "negative"
MIXED = "mixed"
NEUTRAL = "neutral"

# Sobe ou desce, e o sentido se inverte quando o assunto é custo ("queda nos custos" é boa).
MOVEMENT_UP = (
    "alta", "altas", "em alta", "sobe", "sobem", "subiu", "subiram", "subir", "subida", "subidas",
    "aumenta", "aumentam", "aumentou", "aumentaram", "aumento", "aumentos",
    "eleva", "elevam", "elevou", "elevaram", "elevar",
    "cresce", "crescem", "cresceu", "cresceram", "crescer", "crescimento",
    "avanca", "avancam", "avancou", "avancaram", "avancar", "avanco", "avancos",
)
MOVEMENT_DOWN = (
    "queda", "quedas", "em queda", "cai", "caem", "caiu", "cairam", "cair",
    "recua", "recuam", "recuou", "recuaram", "recuar", "recuo",
    "baixa", "baixas", "em baixa", "despenca", "despencam", "despencou", "desaba", "desabam", "desabou",
    "tomba", "tombam", "tombou", "tombo", "retracao",
)
POSITIVE_TERMS = (
    "valoriza", "valorizam", "valorizou", "valorizacao", "valorizado", "valorizada",
    "recorde", "recordes", "maior desde", "maior patamar", "mais caro", "mais cara", "mais caros", "mais caras",
    "sustenta", "sustentam", "suporte", "firme", "firmes",
    "recupera", "recuperam", "recuperou", "recuperaram", "recuperacao", "retomada",
    "ganho", "ganhos", "lucro", "lucros", "expansao", "novos mercados", "novo mercado", "abre mercado",
    "otimismo", "otimista", "otimistas", "positivo", "positiva", "positivos", "positivas",
    "favorece", "favorecem", "favorecer", "favoravel", "favoraveis",
    "beneficia", "beneficiam", "beneficiar", "beneficio", "beneficios",
    "impulso", "impulsiona", "impulsionam", "impulsionou", "impulsionado", "impulsionada",
    "melhora", "melhoram", "melhorou", "melhorar", "excelente", "abre portas",
    "bom inicio", "boa safra", "boas perspectivas", "boa produtividade", "boas condicoes", "condicao boa",
    "alta produtividade", "alta qualidade", "alta demanda", "forte demanda",
    "demanda aquecida", "aquecida", "aquecido", "aquecidas", "aquecidos",
)
NEGATIVE_TERMS = (
    "desvaloriza", "desvalorizam", "desvalorizou", "desvalorizacao",
    "mais barato", "mais barata", "mais baratos", "mais baratas", "barateou", "barateiam",
    "perda", "perdas", "prejuizo", "prejuizos", "quebra", "quebras", "quebra de safra", "crise", "crises",
    "risco", "riscos", "ameaca", "ameacam", "ameacou", "incerteza", "incertezas",
    "preocupa", "preocupam", "preocupou", "preocupacao", "preocupacoes", "preocupante",
    "pessimismo", "pessimista", "pessimistas", "dificuldade", "dificuldades",
    "atraso", "atrasos", "atrasa", "atrasam", "atrasou", "pior", "piora", "pioram", "piorou",
    "fraco", "fraca", "fracos", "fracas", "enfraquece", "enfraquecem", "enfraqueceu", "enfraquecimento",
    "afeta", "afetam", "afetar", "afetou", "afetaram", "afetada", "afetado", "afetadas", "afetados",
    "perde forca", "perdem forca", "perdeu forca", "perderam forca",
    "compromete", "comprometem", "comprometeu", "comprometida", "comprometido",
    "dano", "danos", "destroi", "destroem", "destruiu", "destruiram",
    "pressiona", "pressionam", "pressionou", "pressionada", "pressionado", "pressionadas", "pressionados",
    "limita", "limitam", "limitou", "limitada", "limitado", "limitadas", "limitados",
    "travado", "travada", "travados", "travadas", "lento", "lenta", "lentos", "lentas",
    "divida", "dividas", "recuperacao judicial", "multa", "multas", "embargo", "embargos", "sobretaxa",
    "menor demanda", "menor interesse", "menor producao", "oferta elevada",
    "baixa produtividade", "baixo rendimento", "rendimento mais baixo", "reducao da producao",
    "reducao na producao", "reducao de area", "excesso de chuva", "excesso de chuvas", "excesso de umidade",
    "geada", "geadas", "estiagem", "seca", "secas", "granizo", "enchente", "enchentes",
    "inundacao", "inundacoes", "praga", "pragas", "doenca", "doencas", "virus", "virose", "viroses",
    "surto", "surtos", "greening", "ferrugem", "vassoura de bruxa",
)
# Parecem sinais, mas não dizem nada sobre a cultura: saem do texto antes da busca no léxico.
NOT_SIGNALS = (
    "alta do dolar", "alta da moeda", "queda do dolar", "baixa do dolar",
    "alta temperatura", "altas temperaturas", "alta umidade", "alta tecnologia",
    "baixa temperatura", "baixas temperaturas", "baixa umidade",
    "queda de temperatura", "queda das temperaturas", "reducao dos estoques",
    "pressionaram a inflacao", "pressiona a inflacao", "pressionam a inflacao",
    "carne seca", "fruta seca", "frutas secas", "materia seca", "massa seca", "terras baixas",
    # Pouca oferta sustenta o preço: não é ruim para quem vende.
    "baixa oferta",
    # Progresso do trabalho no campo não é notícia boa nem ruim.
    "colheita avanca", "plantio avanca", "semeadura avanca", "semeadura avancou",
    "avanco da colheita", "avanco do plantio", "avanco da semeadura",
)
# A palavra da cultura aqui não é a cultura ("alerta laranja" é aviso de chuva).
NOT_THE_CROP = re.compile(
    r"caf[ée] da manh[ãa]"
    r"|(?:alerta|sinal|bandeira|cor|empresas?|contas?|agosto)\s+laranja"
    r"|pre[çc]o de banana|rep[úu]blica das bananas"
    r"|mangas?\s+(?:longas?|curtas?)|arrega[çc]\w+\s+as\s+mangas|carta\s+na\s+manga"
    r"|ma[çc][ãa] do rosto|mam[ãa]o com a[çc][úu]car"
)
# Título sobre evento ou culinária, não sobre a lavoura. "Receita" sozinha também é faturamento.
OFF_TOPIC_TITLE = re.compile(
    r"(?<!\w)(?:festas?|festival|gastronomia|gastron[ôo]mic\w+|culin[áa]ri\w+|sobremesas?|bolos?|drinks?|receitas)(?!\w)"
    r"|(?<!\w)receita de (?!us\b|r\$|\d)"
)
# Culturas fora do modelo, que também dividem manchete com as dele.
OTHER_CROP_TERMS = (
    "soja", "trigo", "cana", "cana-de-açúcar", "açúcar", "cacau", "amendoim", "mandioca",
    "tomate", "cebola", "batata", "cenoura", "sorgo", "cevada", "aveia", "girassol", "canola",
)

COST_WINDOW = 4  # palavras em volta de um movimento em que o custo inverte o sentido
_COST = re.compile(r"(?<!\w)(?:custos?|insumos?|fertilizantes?|fretes?|d[ií]vidas?|inflacao)(?!\w)")
_NEGATED = re.compile(
    r"(?<![\w-])(?:sem|nao|nem|nunca|menos|contra|livres? de|evit\w+|reduz\w*|reducao de|combat\w+|combate a"
    r"|control\w+|afast\w+|proteg\w+|resist\w+)\s+(?:[\w-]+\s+){0,3}$"
)
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\s+[|–—]\s+")
# Depois de "mas", a oração sem sujeito ainda fala da mesma cultura: "café cresce, mas cai em receita".
_CLAUSE = re.compile(
    r",?\s+(?P<same>mas|porém|contudo|entretanto|todavia|no entanto)\s+"
    r"|,?\s+(?P<new>enquanto|embora|apesar)(?=\s)"
)
_PARTS = re.compile(r",\s+|\s+e\s+")


def is_valid_sentiment(value: object) -> bool:
    return value in (POSITIVE, NEGATIVE, MIXED, NEUTRAL)


@dataclass(frozen=True)
class Classification:
    about_crop: bool
    sentiment: str
    positive: tuple[str, ...] = ()
    negative: tuple[str, ...] = ()
    source: str = "rules"  # "rules" ou "llm" (services/llm_reader.py)
    model: Optional[str] = None  # o modelo de IA, quando source é "llm"

    @property
    def signals(self) -> list[str]:
        """As palavras que decidiram: as do lado que venceu, ou as dos dois quando dividida."""
        winners = {POSITIVE: self.positive, NEGATIVE: self.negative}.get(self.sentiment)
        return list(dict.fromkeys(winners if winners is not None else (*self.positive, *self.negative)))


@dataclass(frozen=True)
class _Term:
    polarity: str
    movement: bool
    pattern: re.Pattern[str]


def _word_pattern(term: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(rf"(?<![\w-]){body}(?![\w-])")


def _lexicon() -> list[_Term]:
    entries = [(term, POSITIVE, True) for term in MOVEMENT_UP]
    entries += [(term, NEGATIVE, True) for term in MOVEMENT_DOWN]
    entries += [(term, POSITIVE, False) for term in POSITIVE_TERMS]
    entries += [(term, NEGATIVE, False) for term in NEGATIVE_TERMS]
    # Expressão mais longa primeiro: "recuperacao judicial" antes de "recuperacao".
    entries.sort(key=lambda entry: -len(entry[0]))
    return [_Term(polarity, movement, _word_pattern(term)) for term, polarity, movement in entries]


_TERMS = _lexicon()
_NOT_SIGNALS = [_word_pattern(term) for term in sorted(NOT_SIGNALS, key=len, reverse=True)]
_MATCHERS = {crop_id: CropMatcher(profile) for crop_id, profile in CROPS.items()}


@lru_cache(maxsize=4096)
def _fold_char(char: str) -> str:
    folded = normalize(char)
    return folded if len(folded) == 1 else char


def _fold(text: str) -> str:
    """Tira os acentos mantendo as posições: o sinal é mostrado com a grafia original."""
    return "".join(_fold_char(char) for char in text)


def _blank(text: str, start: int, end: int) -> str:
    return f"{text[:start]}{' ' * (end - start)}{text[end:]}"


def _is_negated(folded: str, start: int) -> bool:
    return bool(_NEGATED.search(folded[:start]))


def _is_about_cost(folded: str, start: int, end: int) -> bool:
    before = folded[:start].split()[-COST_WINDOW:]
    after = folded[end:].split()[:COST_WINDOW]
    return bool(_COST.search(" ".join((*before, *after))))


def _signals(text: str) -> tuple[list[str], list[str]]:
    """(sinais positivos, sinais negativos) do trecho, na grafia original."""
    folded = _fold(text)
    remaining = folded
    for pattern in _NOT_SIGNALS:
        for match in pattern.finditer(remaining):
            remaining = _blank(remaining, *match.span())
    positive: list[str] = []
    negative: list[str] = []
    for term in _TERMS:
        for match in term.pattern.finditer(remaining):
            start, end = match.span()
            remaining = _blank(remaining, start, end)
            if _is_negated(folded, start):
                continue
            polarity = term.polarity
            if term.movement and _is_about_cost(folded, start, end):
                polarity = NEGATIVE if polarity == POSITIVE else POSITIVE
            (positive if polarity == POSITIVE else negative).append(text[start:end])
    return positive, negative


@lru_cache(maxsize=len(CROPS))
def _other_crops(crop_id: str) -> re.Pattern[str]:
    own = set(CROPS[crop_id].terms)
    terms = {term for profile in CROPS.values() for term in profile.terms} | set(OTHER_CROP_TERMS)
    alternatives = "|".join(re.escape(term) for term in sorted(terms - own, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})s?(?!\w)")


def _clean(text: str) -> str:
    return NOT_THE_CROP.sub(" ", " ".join(text.split()).lower())


def _clauses(sentence: str) -> Iterable[tuple[str, bool]]:
    """(oração, continua o assunto da oração anterior)."""
    position, same_subject = 0, False
    for match in _CLAUSE.finditer(sentence):
        yield sentence[position : match.start()], same_subject
        position, same_subject = match.end(), match.group("same") is not None
    yield sentence[position:], same_subject


def _scope_signals(clause: str, profile: CropProfile) -> tuple[list[str], list[str]]:
    """Com outra cultura na oração, procura primeiro no pedaço que cita esta."""
    if _other_crops(profile.id).search(clause):
        matcher = _MATCHERS[profile.id]
        positive: list[str] = []
        negative: list[str] = []
        for part in _PARTS.split(clause):
            if matcher.match(part):
                part_positive, part_negative = _signals(part)
                positive += part_positive
                negative += part_negative
        if positive or negative:
            return positive, negative
    return _signals(clause)


def _scan(text: str, profile: CropProfile) -> tuple[bool, list[str], list[str]]:
    """(cita a cultura, sinais positivos e negativos das orações sobre ela)."""
    matcher = _MATCHERS[profile.id]
    mentioned = False
    positive: list[str] = []
    negative: list[str] = []
    for sentence in _SENTENCE.split(text):
        in_subject = False
        for clause, same_subject in _clauses(sentence):
            if matcher.match(clause):
                mentioned = in_subject = True
                scope = _scope_signals(clause, profile)
            elif same_subject and in_subject and not _other_crops(profile.id).search(clause):
                scope = _signals(clause)
            else:
                in_subject = False
                continue
            positive += scope[0]
            negative += scope[1]
    return mentioned, positive, negative


def _verdict(positive: list[str], negative: list[str]) -> str:
    if len(positive) > len(negative):
        return POSITIVE
    if len(negative) > len(positive):
        return NEGATIVE
    return MIXED if positive else NEUTRAL


def classify_article(profile: CropProfile, title: str, summary: Optional[str] = None) -> Classification:
    """Citar no título basta para ser da cultura. Só no resumo, é preciso dizer algo sobre ela:

    "inseticida usado em culturas como soja, milho e algodão" não é notícia de milho.
    """
    clean_title, clean_summary = _clean(title), _clean(summary or "")
    if OFF_TOPIC_TITLE.search(clean_title):
        return Classification(about_crop=False, sentiment=NEUTRAL)

    in_title, positive, negative = _scan(clean_title, profile)
    in_summary = False
    if not (in_title and (positive or negative)):
        in_summary, positive, negative = _scan(clean_summary, profile)
        if in_title and not (positive or negative):
            # A cultura é o assunto da notícia: vale o restante do texto, se não citar outra.
            whole = f"{clean_title}. {clean_summary}"
            if not _other_crops(profile.id).search(whole):
                positive, negative = _signals(whole)

    about_crop = in_title or (in_summary and bool(positive or negative))
    if not about_crop:
        return Classification(about_crop=False, sentiment=NEUTRAL)
    return Classification(True, _verdict(positive, negative), tuple(positive), tuple(negative))
