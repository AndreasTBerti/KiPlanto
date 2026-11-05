"""Regras de relevância das notícias (SPEC §5.4) e mapa cultura do modelo → termos."""
from datetime import datetime, timedelta, timezone

import pytest

from services.news.crops import CROPS, get_crop
from services.news.relevance import (
    CropMatcher,
    LocationMatcher,
    article_id,
    canonical_url,
    deduplicate,
    harvest_score,
    normalize,
    rank,
    recency_score,
    score_item,
    title_key,
    within_window,
)
from services.news.sources import Location, RawItem

NOW = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
TUPA = Location(city="Tupã", state="São Paulo", uf="SP")


def make_item(title, summary=None, *, url="https://example.com/a", days_ago=1, image=None, feed="canal_rural"):
    return RawItem(
        title=title,
        summary=summary,
        url=url,
        source_name="Fonte",
        source_feed=feed,
        published_at=None if days_ago is None else NOW - timedelta(days=days_ago),
        image_url=image,
    )


def match(text, location, location_filtered=False):
    return LocationMatcher(location).match(text, location_filtered)


# --- tema ---------------------------------------------------------------------

def test_normalize_removes_accents_and_case():
    assert normalize("Colheita de Café em SÃO Paulo") == "colheita de cafe em sao paulo"


def test_whole_word_canal_is_not_cana():
    assert harvest_score("Canal Rural transmite leilão") == (0, [])
    assert harvest_score("Cana-de-açúcar ganha espaço")[1] == ["cana"]


def test_plural_and_accent_insensitive_terms():
    score, keywords = harvest_score("Safras de CAFÉ e algodao")
    assert keywords == ["safra", "café", "algodão"]
    assert score == 3 + 1 + 1


def test_harvest_score_weights_and_cap():
    assert harvest_score("Colheita avança")[0] == 3
    assert harvest_score("Soja, milho e trigo")[0] == 3
    assert harvest_score("Colheita, safra e plantio")[0] == 6  # 9 limitado ao teto


# --- localidade ----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Safra de café em Franca (SP)",
    "Safra de café em Franca/SP",
    "Safra de café em Franca - SP",
    "Safra de café cresce em SP",
    "Safra de café cresce em São Paulo",
])
def test_state_matches_name_or_uppercase_uf(text):
    assert match(text, TUPA) == "state"


def test_city_match_beats_state_and_accepts_uppercase():
    assert match("Colheita em Tupã (SP)", TUPA) == "city"
    assert match("COLHEITA EM TUPÃ", TUPA) == "city"


def test_inferred_only_for_location_filtered_sources():
    assert match("Colheita de amendoim avança", TUPA, location_filtered=True) == "inferred"
    assert match("Colheita de amendoim avança", TUPA, location_filtered=False) is None


@pytest.mark.parametrize("location, text", [
    (Location("Aracaju", "Sergipe", "SE"), "Colheita de milho atrasa se a chuva continuar"),
    (Location("Belém", "Pará", "PA"), "Safra de soja para exportação bate recorde"),
    (Location("Belém", "Pará", "PA"), "Safra de soja bate recorde no Paraná"),
    (Location("Sorriso", "Mato Grosso", "MT"), "Safra recorde traz sorriso aos produtores"),
    (Location("Sorriso", "Mato Grosso", "MT"), "Colheita de soja avança em Mato Grosso do Sul"),
    (Location("Palmas", "Tocantins", "TO"), "Produtores batem palmas para a safra"),
    (Location("Tupã", "São Paulo", "SP"), "Colheita de café em sp"),
])
def test_locality_false_positives_are_discarded(location, text):
    assert match(text, location) is None


def test_mato_grosso_still_matches_next_to_mato_grosso_do_sul():
    mt = Location("Sorriso", "Mato Grosso", "MT")
    assert match("Safra em Mato Grosso do Sul e Mato Grosso", mt) == "state"
    assert match("Safra em Mato Grosso do Sul", Location("Dourados", "Mato Grosso do Sul", "MS")) == "state"


def test_common_word_city_matches_only_capitalized():
    sorriso = Location("Sorriso", "Mato Grosso", "MT")
    assert match("Colheita de soja avança em Sorriso", sorriso) == "city"


# --- recência, janela e score ----------------------------------------------------

def test_recency_score():
    assert recency_score(NOW - timedelta(days=7), NOW) == 2
    assert recency_score(NOW - timedelta(days=8), NOW) == 1
    assert recency_score(NOW - timedelta(days=31), NOW) == 0
    assert recency_score(None, NOW) == 0


def test_within_window_keeps_undated_items():
    assert within_window(None, NOW, 30)
    assert within_window(NOW - timedelta(days=29), NOW, 30)
    assert not within_window(NOW - timedelta(days=31), NOW, 30)


def test_spec_example_scores_nine():
    # Item real do Canal Rural em 2026-11-03 (SPEC §5.5): safra 3 + trigo 1 + SP 3 + recência 2.
    item = make_item(
        "Chuvas podem reduzir safra de trigo de SP a menos de 20% do previsto",
        "Precipitações em setembro prejudicaram a produção e a qualidade dos grãos",
        days_ago=0,
    )
    scored = score_item(item, location=LocationMatcher(TUPA), location_filtered=False, now=NOW)
    assert scored is not None
    assert scored.location_match == "state"
    assert scored.matched_keywords == ["safra", "trigo"]
    assert scored.relevance_score == 9


def test_cutoff_requires_theme_and_location():
    matcher = LocationMatcher(TUPA)
    weak = make_item("Preço da soja sobe em SP")  # tema 1 < 3
    national = make_item("Colheita de soja avança nos EUA")  # sem local
    assert score_item(weak, location=matcher, location_filtered=False, now=NOW) is None
    assert score_item(national, location=matcher, location_filtered=False, now=NOW) is None
    assert score_item(national, location=matcher, location_filtered=True, now=NOW).location_match == "inferred"


def test_false_positive_theme_needs_location_too():
    item = make_item("Empresa abre safra de talentos com 200 vagas")
    assert score_item(item, location=LocationMatcher(TUPA), location_filtered=False, now=NOW) is None


# --- cultura recomendada pelo modelo ---------------------------------------------

def test_crop_bonus_and_keywords():
    crop = CropMatcher(get_crop("maize"))
    item = make_item("Colheita de milho avança em SP", days_ago=10)
    base = score_item(item, location=LocationMatcher(TUPA), location_filtered=False, now=NOW)
    boosted = score_item(item, location=LocationMatcher(TUPA), location_filtered=False, now=NOW, crop=crop)
    assert not base.crop_match and boosted.crop_match
    assert boosted.relevance_score == base.relevance_score + 3
    assert boosted.matched_keywords == ["colheita", "milho"]  # sem duplicar "milho"


def _with_crop(title, *, agro_source, location_filtered=False, crop_id="papaya"):
    return score_item(
        make_item(title),
        location=LocationMatcher(TUPA),
        location_filtered=location_filtered,
        now=NOW,
        crop=CropMatcher(get_crop(crop_id)),
        agro_source=agro_source,
    )


def test_crop_in_agro_source_waives_the_harvest_theme():
    scored = _with_crop("Preço do mamão sobe em SP", agro_source=True)
    assert scored.location_match == "state" and scored.tier == 2


def test_crop_in_agro_source_without_location_is_outside():
    scored = _with_crop("Preço do mamão sobe no Espírito Santo", agro_source=True)
    assert scored.location_match == "outside" and scored.tier == 1


def test_general_news_feed_still_requires_the_theme():
    # "manga" em feed de notícias gerais pode ser de camisa, não a fruta.
    assert _with_crop("Camisa de manga longa volta à moda em SP", agro_source=False, crop_id="mango") is None
    assert _with_crop("Camisa de manga longa volta à moda", agro_source=False, location_filtered=True,
                      crop_id="mango") is None


def test_other_crops_without_location_stay_out_even_in_agro_source():
    assert _with_crop("Colheita de soja avança nos EUA", agro_source=True) is None


def test_rank_puts_crop_tiers_first():
    region = _with_crop("Preço do mamão sobe em SP", agro_source=True)
    outside = _with_crop("Colheita de mamão bate recorde no Espírito Santo", agro_source=True)
    other_crop = _with_crop("Colheita e plantio de soja em Tupã", agro_source=True)
    assert rank([other_crop, outside, region]) == [region, outside, other_crop]


def test_crop_terms_keep_accents():
    assert CropMatcher(get_crop("pomegranate")).match("Safra em Roma") == []
    assert CropMatcher(get_crop("pomegranate")).match("Safra de romã") == ["romã"]
    assert CropMatcher(get_crop("apple")).match("Safra de MAÇÃS no Sul") == ["maçã"]


def test_crop_terms_added_to_keywords_when_not_theme_terms():
    crop = CropMatcher(get_crop("watermelon"))
    item = make_item("Colheita de melancia começa em SP")
    scored = score_item(item, location=LocationMatcher(TUPA), location_filtered=False, now=NOW, crop=crop)
    assert scored.matched_keywords == ["colheita", "melancia"]


def test_get_crop_is_case_insensitive_and_tolerates_none():
    assert get_crop(" Maize ").name == "Milho"
    assert get_crop(None) is None
    assert get_crop("inexistente") is None


def test_crop_map_covers_every_model_class():
    from model.crop_model import get_model

    classes = {str(c) for c in get_model().classes_}
    assert classes <= set(CROPS), f"classes sem termos de notícia: {sorted(classes - set(CROPS))}"


# --- deduplicação e ordenação ---------------------------------------------------

def _scored(item, location_filtered=False, crop=None):
    return score_item(item, location=LocationMatcher(TUPA), location_filtered=location_filtered, now=NOW, crop=crop)


def test_canonical_url_and_id_ignore_query_fragment_and_scheme():
    a = "https://g1.globo.com/sp/noticia/x.ghtml?utm_source=rss#topo"
    b = "http://G1.globo.com/sp/noticia/x.ghtml/"
    assert canonical_url(a) == canonical_url(b) == "g1.globo.com/sp/noticia/x.ghtml"
    assert article_id(a) == article_id(b)
    assert len(article_id(a)) == 16


def test_title_key_ignores_case_accents_and_punctuation():
    assert title_key("Colheita de café: avanço em SP!") == title_key("colheita de cafe  avanco em sp")


def test_dedup_prefers_image_then_best_location():
    url = "https://g1.globo.com/sp/noticia/colheita.ghtml"
    from_state_feed = _scored(make_item("Colheita de amendoim avança", url=url, feed="g1_estadual"),
                              location_filtered=True)
    with_image = _scored(make_item("Colheita de amendoim avança em SP", url=url + "?utm=x",
                                   image="https://img.example/1.jpg", feed="g1_agro"))
    kept = deduplicate([from_state_feed, with_image])
    assert kept == [with_image]


def test_dedup_by_title_across_sources():
    a = _scored(make_item("Safra de trigo em SP tem quebra", url="https://a.example/1"))
    b = _scored(make_item("Safra de trigo em SP tem quebra!", url="https://b.example/2"))
    c = _scored(make_item("Colheita de cana começa em SP", url="https://c.example/3"))
    assert len(deduplicate([a, b, c])) == 2


def test_rank_by_score_then_date():
    older = _scored(make_item("Colheita em SP", url="https://a.example/1", days_ago=3))
    newer = _scored(make_item("Plantio em SP", url="https://a.example/2", days_ago=1))
    best = _scored(make_item("Colheita em Tupã", url="https://a.example/3", days_ago=20))
    assert rank([older, newer, best]) == [best, newer, older]
