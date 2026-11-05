"""Unidades federativas do Brasil: sigla, nome e feed estadual do g1.

`g1_feed` é o trecho usado em https://g1.globo.com/rss/g1/{g1_feed}/
(as 27 UFs foram validadas em 2026-11-03: HTTP 200 com 100 itens).
"""

import unicodedata
from typing import Dict, Optional

BR_STATES: Dict[str, Dict[str, str]] = {
    "AC": {"name": "Acre", "g1_feed": "ac"},
    "AL": {"name": "Alagoas", "g1_feed": "al"},
    "AP": {"name": "Amapá", "g1_feed": "ap"},
    "AM": {"name": "Amazonas", "g1_feed": "am"},
    "BA": {"name": "Bahia", "g1_feed": "ba"},
    "CE": {"name": "Ceará", "g1_feed": "ce"},
    "DF": {"name": "Distrito Federal", "g1_feed": "df"},
    "ES": {"name": "Espírito Santo", "g1_feed": "es"},
    "GO": {"name": "Goiás", "g1_feed": "go"},
    "MA": {"name": "Maranhão", "g1_feed": "ma"},
    "MT": {"name": "Mato Grosso", "g1_feed": "mt"},
    "MS": {"name": "Mato Grosso do Sul", "g1_feed": "ms"},
    "MG": {"name": "Minas Gerais", "g1_feed": "mg"},
    "PA": {"name": "Pará", "g1_feed": "pa"},
    "PB": {"name": "Paraíba", "g1_feed": "pb"},
    "PR": {"name": "Paraná", "g1_feed": "pr"},
    "PE": {"name": "Pernambuco", "g1_feed": "pe"},
    "PI": {"name": "Piauí", "g1_feed": "pi"},
    "RJ": {"name": "Rio de Janeiro", "g1_feed": "rj"},
    "RN": {"name": "Rio Grande do Norte", "g1_feed": "rn"},
    "RS": {"name": "Rio Grande do Sul", "g1_feed": "rs"},
    "RO": {"name": "Rondônia", "g1_feed": "ro"},
    "RR": {"name": "Roraima", "g1_feed": "rr"},
    "SC": {"name": "Santa Catarina", "g1_feed": "sc"},
    "SP": {"name": "São Paulo", "g1_feed": "sp"},
    "SE": {"name": "Sergipe", "g1_feed": "se"},
    "TO": {"name": "Tocantins", "g1_feed": "to"},
}

_STATE_PREFIXES = ("estado de ", "estado do ", "estado da ")


def _fold(text: str) -> str:
    """Minúsculas, sem acentos e com espaços normalizados ("São  Paulo" -> "sao paulo")."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    folded = " ".join(without_accents.casefold().split())
    for prefix in _STATE_PREFIXES:
        if folded.startswith(prefix):
            return folded[len(prefix):]
    return folded


_UF_BY_FOLDED_NAME = {_fold(info["name"]): uf for uf, info in BR_STATES.items()}


def normalize_uf(value: Optional[str]) -> Optional[str]:
    """Devolve a sigla da UF a partir de uma sigla ("sp") ou de um nome ("São Paulo").

    Retorna None quando o valor está vazio ou não corresponde a nenhuma UF,
    por exemplo um `admin1` do geocodificador que não seja um estado brasileiro.
    """
    if not value or not value.strip():
        return None
    text = value.strip()
    if text.upper() in BR_STATES:
        return text.upper()
    return _UF_BY_FOLDED_NAME.get(_fold(text))


def state_name(uf: Optional[str]) -> Optional[str]:
    """Nome do estado para uma sigla válida ("SP" -> "São Paulo"); None caso contrário."""
    normalized = normalize_uf(uf)
    return BR_STATES[normalized]["name"] if normalized else None
