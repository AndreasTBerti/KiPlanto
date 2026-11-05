"""Ponte entre o modelo de ML e as notícias: classe do modelo → termos em português.

`GET /news?crop=maize` usa estes termos para dar bônus às notícias que citam a cultura
recomendada (SPEC §10, item 10). As chaves precisam cobrir `model.classes_`
(verificado em tests/test_news_relevance.py).

Os termos são casados no texto em minúsculas **com acento**, como palavra inteira:
"romã" não pode casar com "Roma", nem "maçã" com "maca".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropProfile:
    id: str
    name: str
    terms: tuple[str, ...]


def _crop(crop_id: str, name: str, *terms: str) -> CropProfile:
    return CropProfile(crop_id, name, terms)


# Nomes iguais aos de CROP_DICTIONARY (frontend/src/types/api.ts).
# As variedades de feijão do dataset indiano não têm cobertura própria na imprensa
# brasileira; "feijão" funciona como aproximação para todas elas.
CROPS: dict[str, CropProfile] = {
    c.id: c
    for c in (
        _crop("apple", "Maçã", "maçã", "pomicultura"),
        _crop("banana", "Banana", "banana", "bananicultura"),
        _crop("blackgram", "Feijão-Preto (Vigna)", "feijão-preto", "feijão"),
        _crop("chickpea", "Grão-de-Bico", "grão-de-bico"),
        _crop("coconut", "Coco", "coco", "coqueiro"),
        _crop("coffee", "Café", "café", "cafeicultura", "cafeicultor"),
        _crop("cotton", "Algodão", "algodão", "cotonicultura"),
        _crop("grapes", "Uva", "uva", "videira", "viticultura"),
        _crop("jute", "Juta", "juta"),
        _crop("kidneybeans", "Feijão Vermelho", "feijão"),
        _crop("lentil", "Lentilha", "lentilha"),
        _crop("maize", "Milho", "milho"),
        _crop("mango", "Manga", "manga", "mangicultura"),
        _crop("mothbeans", "Feijão-Moth", "feijão"),
        _crop("mungbean", "Feijão-Mungo", "feijão-mungo", "feijão"),
        _crop("muskmelon", "Melão Cantaloupe", "melão"),
        _crop("orange", "Laranja", "laranja", "citricultura", "citros"),
        _crop("papaya", "Mamão", "mamão"),
        _crop("pigeonpeas", "Feijão-Guandu", "feijão-guandu", "guandu", "feijão"),
        _crop("pomegranate", "Romã", "romã"),
        _crop("rice", "Arroz", "arroz", "rizicultura"),
        _crop("watermelon", "Melancia", "melancia"),
    )
}


def get_crop(crop_id: str | None) -> CropProfile | None:
    if not crop_id:
        return None
    return CROPS.get(crop_id.strip().lower())
