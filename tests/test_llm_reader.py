"""Testes da leitura por IA (services/openrouter.py e services/llm_reader.py), sem rede."""
import json
from datetime import datetime, timezone

import pytest
import requests
from fastapi.testclient import TestClient

import main
from schemas.news_schema import NewsArticle, NewsLocation, NewsResponse
from services import cross_recommendation as cross
from services import llm_reader, openrouter
from services.llm_reader import NewsItem

FEATURES = {"n": 60, "p": 45, "k": 50, "temperature": 24, "humidity": 70, "rainfall": 120}
MODEL = "vendor/modelo-barato"


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("sem JSON")
        return self._body


def reply(data, finish_reason="stop"):
    content = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return FakeResponse(200, {"choices": [{"finish_reason": finish_reason, "message": {"content": content}}]})


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("OPENROUTER_MODELS", MODEL)


def fake_post(monkeypatch, responder):
    calls = []

    def post(url, headers=None, json=None, timeout=None):  # noqa: A002
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return responder(json)

    monkeypatch.setattr(openrouter.requests, "post", post)
    return calls


def schema_call(**kwargs):
    return openrouter.chat_json("s", "u", schema_name="x", schema={}, max_tokens=10, **kwargs)


# --- travas de gasto ---------------------------------------------------------

def paid_reply(cost):
    response = reply({"ok": True})
    response._body["usage"] = {"cost": cost}
    return response


def test_every_request_carries_the_price_cap(monkeypatch, enabled):
    calls = fake_post(monkeypatch, lambda body: reply({"ok": True}))

    schema_call()

    assert calls[0]["json"]["provider"]["max_price"] == {"prompt": 0.20, "completion": 0.50}
    assert calls[0]["json"]["provider"]["require_parameters"] is True


def test_price_cap_comes_from_the_environment(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MAX_INPUT_PRICE", "0.05")
    monkeypatch.setenv("OPENROUTER_MAX_OUTPUT_PRICE", "0.10")
    calls = fake_post(monkeypatch, lambda body: reply({"ok": True}))

    schema_call()

    assert calls[0]["json"]["provider"]["max_price"] == {"prompt": 0.05, "completion": 0.10}


def test_invalid_price_cap_keeps_the_default_instead_of_removing_it(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MAX_INPUT_PRICE", "abc")
    monkeypatch.setenv("OPENROUTER_MAX_OUTPUT_PRICE", "-1")
    calls = fake_post(monkeypatch, lambda body: reply({"ok": True}))

    schema_call()

    assert calls[0]["json"]["provider"]["max_price"] == {"prompt": 0.20, "completion": 0.50}


def test_budget_turns_the_llm_off(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MAX_SPEND_USD", "0.01")
    calls = fake_post(monkeypatch, lambda body: paid_reply(0.006))

    schema_call()
    schema_call()
    assert openrouter.spent_usd() == pytest.approx(0.012)
    assert openrouter.is_enabled() is False

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()
    assert len(calls) == 2


def test_budget_counts_answers_that_failed_validation(monkeypatch, enabled):
    fake_post(monkeypatch, lambda body: FakeResponse(200, {
        "choices": [{"finish_reason": "length", "message": {"content": "cortado"}}],
        "usage": {"cost": 0.002},
    }))

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()

    assert openrouter.spent_usd() == pytest.approx(0.002)


def test_budget_stops_the_fallback_models_too(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MODELS", "a/um,b/dois")
    monkeypatch.setenv("OPENROUTER_MAX_SPEND_USD", "0.001")
    calls = fake_post(monkeypatch, lambda body: FakeResponse(200, {
        "choices": [{"message": {"content": "cortado"}}],
        "usage": {"cost": 0.002},
    }))

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()

    assert [call["json"]["model"] for call in calls] == ["a/um"]


def test_reader_makes_no_request_when_the_budget_is_over(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MAX_SPEND_USD", "0.001")
    openrouter._add_spend(0.01)
    calls = fake_post(monkeypatch, lambda body: reply({"items": []}))

    assert llm_reader.classify_news([NewsItem("coffee", "1", "Café sobe")]) == {}
    assert llm_reader.write_conclusion(CANDIDATES, "base") is None
    assert calls == []


def test_no_key_turns_the_llm_off_without_any_request(monkeypatch):
    calls = fake_post(monkeypatch, lambda body: reply({"ok": True}))

    assert llm_reader.classify_news([NewsItem("coffee", "1", "Café sobe")]) == {}
    assert calls == []


# --- cliente -----------------------------------------------------------------

def test_request_carries_the_key_the_schema_and_the_model(monkeypatch, enabled):
    calls = fake_post(monkeypatch, lambda body: reply({"ok": True}))

    response = schema_call()

    assert response.model == MODEL
    assert response.data == {"ok": True}
    assert calls[0]["headers"]["Authorization"] == "Bearer chave-de-teste"
    assert calls[0]["json"]["model"] == MODEL
    assert calls[0]["json"]["response_format"]["type"] == "json_schema"


def test_next_model_is_tried_after_a_rate_limit(monkeypatch, enabled):
    monkeypatch.setenv("OPENROUTER_MODELS", "a/um,b/dois")
    responses = iter([FakeResponse(429, {}), reply({"ok": True})])
    calls = fake_post(monkeypatch, lambda body: next(responses))

    assert schema_call().model == "b/dois"
    assert [call["json"]["model"] for call in calls] == ["a/um", "b/dois"]


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(429, {}),
        FakeResponse(500, {}),
        FakeResponse(200, None),
        FakeResponse(200, {"choices": []}),
        reply("não é JSON"),
        reply('{"items": [{"id": 0', finish_reason="length"),
        reply("[1, 2]"),
    ],
)
def test_bad_answers_raise_unavailable(monkeypatch, enabled, response):
    fake_post(monkeypatch, lambda body: response)

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()


def test_network_failure_raises_unavailable(monkeypatch, enabled):
    def post(*args, **kwargs):
        raise requests.Timeout("lento")

    monkeypatch.setattr(openrouter.requests, "post", post)

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()


def test_key_never_reaches_the_logs(monkeypatch, enabled, caplog):
    fake_post(monkeypatch, lambda body: FakeResponse(401, {}))

    with pytest.raises(openrouter.LLMUnavailable):
        schema_call()

    assert "chave-de-teste" not in caplog.text


def test_fenced_json_is_accepted(monkeypatch, enabled):
    fake_post(monkeypatch, lambda body: reply('```json\n{"ok": true}\n```'))

    assert schema_call().data == {"ok": True}


# --- classificação -----------------------------------------------------------

def answer(*items):
    return lambda body: reply({"items": list(items)})


def item(index=0, about=True, sentiment="positive", signals=()):
    return {"id": index, "about_crop": about, "sentiment": sentiment, "signals": list(signals)}


def test_classification_is_read_and_tagged(monkeypatch, enabled):
    fake_post(monkeypatch, answer(item(signals=["Café sobe"])))

    result = llm_reader.classify_news([NewsItem("coffee", "1", "Café sobe em NY")])[("coffee", "1")]

    assert (result.about_crop, result.sentiment, result.source, result.model) == (True, "positive", "llm", MODEL)
    assert result.signals == ["Café sobe"]


def test_signals_that_are_not_in_the_text_are_dropped(monkeypatch, enabled):
    fake_post(monkeypatch, answer(item(signals=["inventado", "CAFÉ SOBE", 7])))

    result = llm_reader.classify_news([NewsItem("coffee", "1", "Café sobe")])[("coffee", "1")]

    assert result.signals == ["CAFÉ SOBE"]


def test_long_signals_are_dropped(monkeypatch, enabled):
    long_signal = "benefício econômico de R$ 140,6 milhões no Estado de Santa Catarina"
    fake_post(monkeypatch, answer(item(signals=[long_signal, "eleva"])))

    result = llm_reader.classify_news([NewsItem("rice", "1", f"Arroz eleva: {long_signal}")])[("rice", "1")]

    assert result.signals == ["eleva"]


def test_not_about_the_crop_has_no_sentiment(monkeypatch, enabled):
    fake_post(monkeypatch, answer(item(about=False, sentiment="positive", signals=["carta"])))

    result = llm_reader.classify_news([NewsItem("mango", "1", "A carta na manga")])[("mango", "1")]

    assert (result.about_crop, result.sentiment, result.signals) == (False, "neutral", [])


@pytest.mark.parametrize(
    "bad",
    [
        item(sentiment="otimo"),
        {"id": 0, "about_crop": "sim", "sentiment": "positive", "signals": []},
        item(index=99),
        "nao-e-objeto",
    ],
)
def test_invalid_items_are_left_for_the_rules(monkeypatch, enabled, bad):
    fake_post(monkeypatch, answer(bad))

    assert llm_reader.classify_news([NewsItem("coffee", "1", "Café sobe")]) == {}


def test_answers_are_cached(monkeypatch, enabled):
    calls = fake_post(monkeypatch, answer(item()))
    items = [NewsItem("coffee", "1", "Café sobe")]

    llm_reader.classify_news(items)
    llm_reader.classify_news(items)

    assert len(calls) == 1


def test_news_is_shared_fairly_among_crops_and_capped(monkeypatch, enabled):
    seen = []

    def responder(body):
        seen.extend(json.loads(body["messages"][1]["content"]))
        return reply({"items": []})

    fake_post(monkeypatch, responder)
    items = [NewsItem("coffee", f"c{i}", f"Café {i}") for i in range(30)]
    items += [NewsItem("rice", "r0", "Arroz 0"), NewsItem("banana", "b0", "Banana 0")]

    llm_reader.classify_news(items)

    assert len(seen) == llm_reader.MAX_ITEMS
    assert {"Arroz 0", "Banana 0", "Café 0"} <= {entry["titulo"] for entry in seen}


# --- conclusão ---------------------------------------------------------------

def article(title, summary=None):
    return NewsArticle(
        id=title,
        title=title,
        summary=summary,
        url="https://example.com/a",
        source_name="Fonte",
        source_feed="canal_rural",
        published_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        location_match="state",
        matched_keywords=[],
        crop_match=True,
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


CANDIDATES = cross.combine(
    {"banana": 60.0, "apple": 20.0, "orange": 12.0},
    {"banana": news(), "apple": news(), "orange": news()},
).candidates
FIRST = CANDIDATES[0]
GOOD = "Banana (60%) lidera no modelo, enquanto Maçã (20%) e Laranja (12%) ficam atrás e sem notícias recentes."


def test_good_conclusion_passes():
    assert llm_reader.is_valid_conclusion(GOOD, CANDIDATES, FIRST) is True


@pytest.mark.parametrize(
    "text",
    [
        "curta",
        None,
        "x" * 800,
        "Maçã (20%) e Laranja (12%) têm notícias, sem nada sobre a primeira colocada no modelo.",
        "Banana (75%) lidera no modelo e as notícias confirmam essa leitura para o produtor.",
        "Banana (60%) lidera no modelo e pode render R$ 90 por saca segundo as notícias lidas.",
        "Banana (60%) lidera no modelo, mas vale olhar o café, que está em alta nas notícias.",
        "Banana (60%) lidera no modelo. Veja mais em https://golpe.example para decidir hoje.",
        "Banana (60%) lidera no modelo, <b>com notícias</b> que ajudam a avaliar a escolha.",
    ],
)
def test_bad_conclusions_are_rejected(text):
    assert llm_reader.is_valid_conclusion(text, CANDIDATES, FIRST) is False


def test_rejected_conclusion_keeps_the_rules_text(monkeypatch, enabled):
    fake_post(monkeypatch, lambda body: reply({"conclusion": "Banana (99%) é garantia de lucro neste ano, plante já."}))

    assert llm_reader.write_conclusion(CANDIDATES, "base") is None


def test_valid_conclusion_is_returned_with_its_model(monkeypatch, enabled):
    fake_post(monkeypatch, lambda body: reply({"conclusion": GOOD}))

    assert llm_reader.write_conclusion(CANDIDATES, "base") == (GOOD, MODEL)


# --- rota --------------------------------------------------------------------

@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def route_setup(monkeypatch, news_for):
    monkeypatch.setattr(cross, "get_harvest_news", lambda city, uf=None, days=30, limit=10, crop=None: news_for(crop))
    monkeypatch.setattr(
        cross,
        "select_candidates",
        lambda probabilities: [("banana", 60.0), ("apple", 20.0), ("orange", 12.0)],
    )


def payload():
    return {"city": "Londrina", "state": "PR", **FEATURES}


def test_route_uses_the_llm_reading_and_conclusion(client, monkeypatch, enabled):
    route_setup(monkeypatch, lambda crop: news(article("Banana no Paraná")) if crop == "banana" else news())

    def responder(body):
        if body["response_format"]["json_schema"]["name"] == "news_classification":
            return reply({"items": [item(sentiment="negative", signals=["Banana"])]})
        return reply({"conclusion": GOOD})

    fake_post(monkeypatch, responder)

    body = client.post("/ai/cross-recommendation", json=payload()).json()

    banana = next(c for c in body["candidates"] if c["crop"] == "banana")
    assert banana["outlook"]["sentiment"] == "negative"
    assert banana["outlook"]["articles"][0]["classified_by"] == "llm"
    assert body["report"]["conclusion"] == GOOD
    assert body["report"]["conclusion_by"] == "llm"
    assert body["report"]["model"] == MODEL
    assert f"IA ({MODEL})" in body["report"]["caveat"]


def test_route_falls_back_to_the_rules_when_the_llm_is_down(client, monkeypatch, enabled):
    route_setup(monkeypatch, lambda crop: news(article("Banana cai no Paraná")) if crop == "banana" else news())
    fake_post(monkeypatch, lambda body: FakeResponse(429, {}))

    response = client.post("/ai/cross-recommendation", json=payload())

    assert response.status_code == 200
    body = response.json()
    banana = next(c for c in body["candidates"] if c["crop"] == "banana")
    assert banana["outlook"]["sentiment"] == "negative"
    assert banana["outlook"]["articles"][0]["classified_by"] == "rules"
    assert body["report"]["conclusion_by"] == "rules"
    assert body["report"]["model"] is None
    assert "palavras-chave" in body["report"]["caveat"]


def test_route_without_key_makes_no_llm_request(client, monkeypatch):
    route_setup(monkeypatch, lambda crop: news(article("Banana cai no Paraná")) if crop == "banana" else news())
    calls = fake_post(monkeypatch, lambda body: reply({}))

    assert client.post("/ai/cross-recommendation", json=payload()).status_code == 200
    assert calls == []


def test_llm_signal_without_support_leaves_a_clean_text(client, monkeypatch, enabled):
    route_setup(monkeypatch, lambda crop: news(article("Banana no Paraná")) if crop == "banana" else news())
    fake_post(monkeypatch, lambda body: reply({"items": [item(signals=["inventado"])]}))

    body = client.post("/ai/cross-recommendation", json=payload()).json()

    banana = next(c for c in body["candidates"] if c["crop"] == "banana")
    assert banana["outlook"]["text"] == "Notícias favoráveis na região: 1 de 1."
