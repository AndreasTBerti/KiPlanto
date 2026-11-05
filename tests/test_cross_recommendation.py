"""Testes da recomendação cruzada (services/cross_recommendation.py), sem rede."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import main
from model.crop_model import crop_prev
from schemas.news_schema import NewsArticle, NewsLocation, NewsResponse
from services import cross_recommendation as cross
from services.climate_data_service import CityNotFoundError, ClimateProviderError
from services.news.service import NewsUnavailableError

FEATURES = {"n": 60, "p": 45, "k": 50, "temperature": 24, "humidity": 70, "rainfall": 120}


def article(title, *, match="state", crop_match=True, summary=None):
    return NewsArticle(
        id=title,
        title=title,
        summary=summary,
        url="https://example.com/a",
        source_name="Fonte",
        source_feed="canal_rural",
        published_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        location_match=match,
        matched_keywords=[],
        crop_match=crop_match,
        relevance_score=5,
    )


def news(*articles):
    return NewsResponse(
        location=NewsLocation(city="Londrina", state="Paraná", uf="PR"),
        generated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        cached=False,
        total=len(articles),
        articles=list(articles),
        sources=[],
    )


CLOSE = {"grapes": 33.0, "coffee": 28.0, "banana": 25.0, "maize": 2.0}


# --- candidatas --------------------------------------------------------------

def test_candidates_are_always_the_top_three_even_when_far_from_the_first():
    probabilities = {"jute": 44.0, "rice": 21.0, "coconut": 12.0, "maize": 9.0}

    assert cross.select_candidates(probabilities) == [("jute", 44.0), ("rice", 21.0), ("coconut", 12.0)]


def test_candidates_follow_the_screen_and_skip_the_negligible():
    """model/crop_model.py não mostra culturas com até 1%."""
    probabilities = {"coffee": 98.0, "grapes": 1.5, "maize": 0.5, "rice": 0.0}

    assert cross.select_candidates(probabilities) == [("coffee", 98.0), ("grapes", 1.5)]
    assert cross.select_candidates({"coffee": 0.5, "grapes": 0.4}) == [("coffee", 0.5)]


def test_far_candidates_are_explained_without_saying_there_is_no_other():
    result = cross.combine(
        {"jute": 44.0, "rice": 21.0, "coconut": 12.0},
        {"jute": news(), "rice": news(), "coconut": news()},
    )

    assert [c.crop for c in result.candidates] == ["jute", "rice", "coconut"]
    assert result.explanation == "O modelo indicou Juta (44%), à frente de Arroz (21%) e Coco (12%)."


def test_news_does_not_lift_a_candidate_far_from_the_first():
    result = cross.combine(
        {"jute": 44.0, "rice": 21.0, "coconut": 12.0},
        {"jute": news(), "rice": news(article("Arroz sobe no Paraná")), "coconut": news()},
    )

    assert result.changed is False
    assert [c.crop for c in result.candidates] == ["jute", "rice", "coconut"]
    assert result.candidates[1].outlook.sentiment == "positive"


def test_crop_prev_returns_all_probabilities():
    result = crop_prev({"N": 60, "P": 45, "K": 50, "temperature": 24, "humidity": 70, "rainfall": 120})

    assert len(result["probabilities"]) == 22
    assert sum(result["probabilities"].values()) == pytest.approx(100, abs=0.5)
    assert result["probabilities"][result["crop_recommendation"]] == result["confidence"]


# --- regra -------------------------------------------------------------------

def test_candidate_with_regional_news_passes_one_without():
    result = cross.combine(CLOSE, {
        "grapes": news(),
        "coffee": news(article("Café em alta no Paraná"), article("Colheita do café no PR")),
        "banana": news(),
    })

    assert result.changed is True
    assert (result.model_recommendation, result.recommendation) == ("grapes", "coffee")
    assert [c.crop for c in result.candidates] == ["coffee", "grapes", "banana"]
    assert [c.model_rank for c in result.candidates] == [2, 1, 3]
    assert result.explanation == (
        "O modelo indicou Uva (33%); Café (28%) passou à frente por ter 2 notícias na região."
    )


def test_news_volume_does_not_matter_among_candidates_with_news():
    result = cross.combine(CLOSE, {
        "grapes": news(article("Uva no Paraná")),
        "coffee": news(*[article(f"Café no Paraná {i}") for i in range(9)]),
        "banana": news(),
    })

    assert result.changed is False
    assert [c.crop for c in result.candidates] == ["grapes", "coffee", "banana"]
    assert "também aparece" in result.explanation


def test_no_news_keeps_the_model_order():
    result = cross.combine(CLOSE, {"grapes": news(), "coffee": news(), "banana": news()})

    assert result.changed is False
    assert [c.crop for c in result.candidates] == ["grapes", "coffee", "banana"]
    assert all(c.status == "no_news" for c in result.candidates)
    assert "para desempatar" in result.explanation


def test_news_from_other_regions_is_not_evidence():
    result = cross.combine(CLOSE, {
        "grapes": news(),
        "coffee": news(article("Café em Minas", match="outside")),
        "banana": news(),
    })

    assert result.changed is False
    assert result.candidates[1].regional_news == 0


def test_failed_news_search_keeps_the_model_order():
    """Com a busca de uma candidata fora do ar, a comparação seria injusta."""
    result = cross.combine(CLOSE, {
        "grapes": None,
        "coffee": news(article("Café no Paraná")),
        "banana": news(),
    })

    assert result.changed is False
    assert result.candidates[0].status == "unavailable"
    assert result.candidates[0].news is None
    assert "vale a ordem do modelo" in result.explanation


def test_only_candidate_is_explained():
    result = cross.combine({"coffee": 99.0, "grapes": 0.5}, {"coffee": news()})

    assert result.explanation == "O modelo indicou Café (99%), sem outra cultura com probabilidade relevante."


def test_unfavorable_news_does_not_lift_a_candidate_over_one_without_news():
    result = cross.combine(CLOSE, {
        "grapes": news(),
        "coffee": news(article("Preço do café cai no Paraná")),
        "banana": news(),
    })

    assert result.changed is False
    assert [c.crop for c in result.candidates] == ["grapes", "coffee", "banana"]
    assert result.candidates[1].outlook.sentiment == "negative"


def test_mention_that_is_not_about_the_crop_is_not_evidence():
    result = cross.combine(CLOSE, {
        "grapes": news(),
        "coffee": news(article("Festival de café no Paraná")),
        "banana": news(),
    })

    assert result.changed is False
    assert result.candidates[1].regional_news == 0
    assert result.candidates[1].status == "no_news"
    assert result.candidates[1].outlook.articles == []


# --- report ------------------------------------------------------------------

BANANA_FIRST = {"banana": 34.0, "apple": 30.0, "orange": 26.0}


def test_report_mixes_the_model_order_with_the_news():
    """O exemplo do pedido: as duas primeiras tendem a cair, e a terceira, a subir."""
    result = cross.combine(BANANA_FIRST, {
        "banana": news(article("Banana tende a queda no Paraná")),
        "apple": news(article("Maçã tende a queda no Paraná")),
        "orange": news(article("Laranja tende a subida no Paraná")),
    })

    by_crop = {c.crop: c for c in result.candidates}
    assert by_crop["banana"].outlook.sentiment == "negative"
    assert by_crop["apple"].outlook.sentiment == "negative"
    assert by_crop["orange"].outlook.sentiment == "positive"
    assert by_crop["orange"].outlook.text == "Notícias favoráveis na região: 1 de 1 (subida)."
    assert by_crop["orange"].outlook.articles[0].signals == ["subida"]
    # Laranja está perto da primeira: passa à frente, e o report diz por quê.
    assert result.recommendation == "orange"
    assert result.report.conclusion == (
        "Banana (34%) lidera no modelo, mas as notícias são desfavoráveis. "
        "Laranja (26%), com probabilidade próxima, passou à frente pelas notícias da região."
    )
    assert "palavras-chave" in result.report.caveat


def test_report_warns_when_the_favorable_candidate_is_far_from_the_first():
    result = cross.combine({"banana": 60.0, "apple": 20.0, "orange": 12.0}, {
        "banana": news(article("Banana tende a queda no Paraná")),
        "apple": news(article("Maçã tende a queda no Paraná")),
        "orange": news(article("Laranja tende a subida no Paraná")),
    })

    assert result.changed is False
    assert result.report.conclusion == (
        "Banana (60%) lidera no modelo, mas as notícias são desfavoráveis. "
        "Laranja (12%) tem notícias favoráveis, mas o modelo a considera menos adequada "
        "ao solo e ao clima: avalie antes de trocar."
    )


def test_report_supports_the_first_when_model_and_news_agree():
    result = cross.combine(BANANA_FIRST, {
        "banana": news(article("Banana sobe no Paraná")),
        "apple": news(),
        "orange": news(),
    })

    assert "reúne a maior probabilidade" in result.report.conclusion


def test_report_falls_back_to_the_model_without_signals():
    result = cross.combine(BANANA_FIRST, {"banana": news(), "apple": news(), "orange": news()})

    assert result.report.conclusion == (
        "As notícias não mostram sinal claro de alta ou queda: vale o modelo, com Banana (34%) à frente."
    )
    assert all(c.outlook.sentiment == "no_news" for c in result.candidates)


def test_report_uses_other_regions_when_the_region_has_no_signal():
    result = cross.combine({"coffee": 80.0, "grapes": 5.0}, {
        "coffee": news(article("Café no Paraná"), article("Café recua em Nova York", match="outside")),
        "grapes": news(),
    })

    outlook = result.candidates[0].outlook
    assert (outlook.sentiment, outlook.scope) == ("negative", "other_regions")
    assert outlook.text == "Notícias desfavoráveis em outras regiões: 1 de 1 (recua)."
    assert result.candidates[0].regional_news == 1


def test_report_flags_generic_bean_news():
    result = cross.combine({"grapes": 40.0, "mothbeans": 35.0}, {
        "grapes": news(),
        "mothbeans": news(article("Feijão sobe no Paraná")),
    })

    assert "feijão em geral" in result.candidates[1].outlook.text


def test_report_with_a_single_candidate_does_not_mention_others():
    result = cross.combine({"coffee": 99.0}, {"coffee": news(article("Café recua", match="outside"))})

    assert result.report.conclusion == (
        "Café (99%) lidera no modelo, mas as notícias são desfavoráveis. "
        "É a única com probabilidade relevante no modelo."
    )


def test_report_is_incomplete_when_the_search_failed():
    result = cross.combine(BANANA_FIRST, {"banana": None, "apple": news(), "orange": news()})

    assert result.candidates[0].outlook.sentiment == "unavailable"
    assert "incompleta" in result.report.conclusion


def test_generic_term_does_not_promote_a_bean_class():
    """"feijão" vale para 5 classes do modelo; não diferencia nenhuma delas."""
    probabilities = {"grapes": 33.0, "mothbeans": 30.0}
    result = cross.combine(probabilities, {
        "grapes": news(),
        "mothbeans": news(article("Feijão no Paraná")),
    })

    assert result.changed is False
    assert result.candidates[1].status == "generic_news"
    assert result.candidates[1].regional_news == 1


def test_specific_bean_term_counts_as_evidence():
    result = cross.combine({"grapes": 33.0, "pigeonpeas": 30.0}, {
        "grapes": news(),
        "pigeonpeas": news(article("Feijão-guandu no Paraná")),
    })

    assert result.recommendation == "pigeonpeas"


# --- alertas -----------------------------------------------------------------

def test_risk_term_alerts_and_unfavorable_news_loses_the_tiebreak():
    frost = article("Geada atinge lavouras de uva no Paraná")
    result = cross.combine(CLOSE, {
        "grapes": news(frost),
        "coffee": news(article("Café no Paraná")),
        "banana": news(),
    })

    assert [c.crop for c in result.candidates] == ["coffee", "grapes", "banana"]
    grapes = result.candidates[1]
    assert grapes.status == "alert"
    assert grapes.alerts[0].article_id == frost.id
    assert grapes.alerts[0].terms == ["geada"]
    assert "geada" in grapes.summary


def test_risk_term_is_found_in_the_summary_without_accent():
    result = cross.combine({"coffee": 80.0}, {
        "coffee": news(article("Café no Paraná", summary="DOENÇAS preocupam produtores")),
    })

    assert result.candidates[0].alerts[0].terms == ["doença"]


def test_risk_term_outside_the_region_is_not_an_alert():
    result = cross.combine({"coffee": 80.0}, {"coffee": news(article("Geada no café", match="outside"))})

    assert result.candidates[0].alerts == []


# --- caminho inverso ---------------------------------------------------------

def test_crops_cited_in_the_region_outside_the_candidates_are_listed():
    corn = [article(f"Milho no Paraná {i}", crop_match=False) for i in range(3)]
    result = cross.combine(CLOSE, {"grapes": news(*corn), "coffee": news(*corn), "banana": news()})

    assert [(c.crop, c.mentions, c.probability) for c in result.also_cited] == [("maize", 3, 2.0)]


def test_single_mention_outside_news_and_candidates_are_not_listed():
    result = cross.combine(CLOSE, {
        "grapes": news(
            article("Milho no Paraná", crop_match=False),
            article("Arroz em Goiás", match="outside", crop_match=False),
            article("Arroz na Bahia", match="outside", crop_match=False),
            article("Uva no Paraná"),
            article("Uva na região"),
        ),
        "coffee": news(),
        "banana": news(),
    })

    assert result.also_cited == []


# --- rota --------------------------------------------------------------------

@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def test_route_searches_news_for_each_candidate(client, monkeypatch):
    calls = []

    def fake_news(city, uf=None, days=30, limit=10, crop=None):
        calls.append((city, uf, days, limit, crop))
        return news()

    monkeypatch.setattr(cross, "get_harvest_news", fake_news)
    monkeypatch.setattr(cross, "select_candidates", lambda p: [("grapes", 33.0), ("coffee", 28.0)])

    response = client.post("/ai/cross-recommendation", json={"city": "Londrina", "state": "pr", **FEATURES})

    assert response.status_code == 200
    assert [c["crop"] for c in response.json()["candidates"]] == ["grapes", "coffee"]
    assert sorted(calls, key=lambda c: c[4]) == [
        ("Londrina", "PR", 30, 30, "coffee"),
        ("Londrina", "PR", 30, 30, "grapes"),
    ]


@pytest.mark.parametrize("error", [NewsUnavailableError([]), ClimateProviderError("fora do ar")])
def test_route_survives_news_failure(client, monkeypatch, error):
    def fake_news(*args, **kwargs):
        raise error

    monkeypatch.setattr(cross, "get_harvest_news", fake_news)

    response = client.post("/ai/cross-recommendation", json={"city": "Londrina", "state": "PR", **FEATURES})

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert all(c["status"] == "unavailable" for c in body["candidates"])


def test_route_city_not_found_is_404(client, monkeypatch):
    def fake_news(*args, **kwargs):
        raise CityNotFoundError("não encontrada")

    monkeypatch.setattr(cross, "get_harvest_news", fake_news)

    response = client.post("/ai/cross-recommendation", json={"city": "Inventada", "state": "PR", **FEATURES})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "override",
    [{"state": "XX"}, {"city": " "}, {"n": -1}, {"humidity": 101}],
)
def test_route_rejects_invalid_input(client, override):
    payload = {"city": "Londrina", "state": "PR", **FEATURES, **override}

    assert client.post("/ai/cross-recommendation", json=payload).status_code == 422
