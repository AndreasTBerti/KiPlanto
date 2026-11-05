"""Testes do classificador de notícias (services/news/classifier.py).

Os casos de manchete real foram colhidos dos feeds em 2026-11-05 e rotulados à mão.
"""
import pytest

from services.news.classifier import classify_article
from services.news.crops import CROPS


def classify(crop, title, summary=None):
    return classify_article(CROPS[crop], title, summary)


@pytest.mark.parametrize(
    ("crop", "title", "expected"),
    [
        ("banana", "Banana tende a queda", "negative"),
        ("apple", "Maçã tende a queda", "negative"),
        ("orange", "Laranja tende subida", "positive"),
    ],
)
def test_examples_from_the_request(crop, title, expected):
    result = classify(crop, title)

    assert result.about_crop is True
    assert result.sentiment == expected


REAL_HEADLINES = [
    ("coffee", "Câmbio e oferta elevada mantêm preços do café em queda em Nova York", None, "negative"),
    ("coffee", "Café sobe em Nova York após redução dos estoques certificados", None, "positive"),
    ("coffee", "Alta do dólar sustenta cotações domésticas do café, apesar de baixas externas", None, "positive"),
    ("coffee", "Gigante do café pede recuperação judicial com dívida de R$ 1,6 bilhão", None, "negative"),
    ("coffee", "Apesar do bom início da safra de café 2027/28, clima preocupa", None, "mixed"),
    ("coffee", "Cecafé: exportação de café cresce 3,1% em volume, mas cai 7,1% em receita", None, "mixed"),
    ("rice", "Preço médio do arroz em casca em outubro foi o maior desde fevereiro de 2025", None, "positive"),
    ("rice", "Indústrias abastecidas e menor demanda externa limitam negócios do arroz", None, "negative"),
    ("rice", "Exportações de arroz dão suporte aos preços, mas mercado interno segue lento", None, "mixed"),
    ("rice", "Arroz: plantio da safra do RS atinge 36,8% da área prevista", None, "neutral"),
    ("orange", "Compras limitadas pelas indústrias pressionam cotações da laranja", None, "negative"),
    ("orange", "Embarques de suco de laranja se recuperam em setembro", None, "positive"),
    ("orange", "Chuvas afetam qualidade das laranjas, mas podem beneficiar próxima safra", None, "mixed"),
    ("apple", "Brasil colhe recorde de 1,6 milhão de toneladas de maçãs em 2025/26", None, "positive"),
    ("cotton", "Valorização das fibras naturais abre portas para cotonicultura paranaense", None, "positive"),
    ("watermelon", "Vírus nunca relatado no Brasil pode estar por trás de surto em melancia", None, "negative"),
    (
        "cotton",
        "Biotecnologia está presente em quase 100% das áreas certificadas de soja e algodão no Brasil",
        None,
        "neutral",
    ),
]


@pytest.mark.parametrize(("crop", "title", "summary", "expected"), REAL_HEADLINES)
def test_real_headlines(crop, title, summary, expected):
    result = classify(crop, title, summary)

    assert result.about_crop is True
    assert result.sentiment == expected, (result.positive, result.negative)


# --- sentimento por cultura --------------------------------------------------

def test_each_crop_gets_its_own_sentiment_in_the_same_text():
    title = "Café recua em Nova York"
    summary = "Algodão também recua nesta manhã; suco de laranja sobe"

    assert classify("coffee", title, summary).sentiment == "negative"
    assert classify("cotton", title, summary).sentiment == "negative"
    assert classify("orange", title, summary).sentiment == "positive"


def test_comma_separates_crops_with_opposite_movements():
    assert classify("maize", "Soja sobe, milho cai").sentiment == "negative"
    assert classify("rice", "Soja cai e arroz sobe").sentiment == "positive"


def test_a_list_of_crops_shares_the_verb():
    assert classify("coffee", "Café, cacau e açúcar operam em queda na bolsa").sentiment == "negative"
    assert classify("maize", "Soja recua", "Milho e trigo têm alta nesta manhã").sentiment == "positive"


def test_other_crop_after_while_does_not_lend_its_signal():
    result = classify("maize", "Soja mantém queda", "Milho opera com estabilidade, enquanto trigo sobe com valorização")

    assert result.about_crop is False


def test_title_decides_over_a_summary_on_another_subject():
    result = classify(
        "coffee",
        "Preço do café cai em Nova York",
        "Perspectivas para a safra brasileira são positivas",
    )

    assert result.sentiment == "negative"


def test_summary_decides_when_the_title_has_no_signal():
    assert classify("coffee", "Café no Paraná", "DOENÇAS preocupam produtores").sentiment == "negative"


# --- armadilhas do léxico ----------------------------------------------------

@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Café sem geada neste ano", "neutral"),
        ("Café não registrou perdas", "neutral"),
        ("Produtor de café combate pragas", "neutral"),
        ("Queda nos custos anima produtor de café", "positive"),
        ("Alta de 73% nos custos do café", "negative"),
        ("Café enfrenta altas temperaturas", "neutral"),
        ("Café: alta do dólar anima exportador", "neutral"),
        ("Colheita avança nas lavouras de café", "neutral"),
        ("Baixa oferta de café sustenta cotações", "positive"),
        ("Custo total ainda limita rentabilidade do café", "negative"),
        ("Preços do café em alta, mas reajustes perdem força", "mixed"),
        ("Brasil abre novos mercados para café", "positive"),
    ],
)
def test_negation_costs_and_false_signals(title, expected):
    assert classify("coffee", title).sentiment == expected


def test_signals_keep_the_original_spelling():
    assert classify("cotton", "Valorização do algodão").signals == ["Valorização".lower()]


def test_signals_are_only_the_winning_side():
    assert classify("maize", "Milho recua em Chicago, sobe na B3 e tem negócios travados").signals == [
        "travados",
        "recua",
    ]
    assert set(classify("rice", "Arroz em alta, mas mercado segue lento").signals) == {"em alta", "lento"}


def test_recovery_in_court_is_not_a_recovery():
    result = classify("coffee", "Gigante do café pede recuperação judicial")

    assert result.positive == ()
    assert result.negative == ("recuperação judicial",)


# --- a notícia é da cultura? -------------------------------------------------

@pytest.mark.parametrize(
    ("crop", "title", "summary"),
    [
        ("coffee", "Hotel serve café da manhã regional", None),
        ("orange", "Inmet emite alerta laranja para geada", None),
        ("mango", "Primíparas são a carta na manga durante a seca", None),
        ("grapes", "Festa da Uva de Jundiaí 2027 terá entrada gratuita", None),
        ("banana", "Receita de bolo de banana para o fim de semana", None),
        (
            "cotton",
            "Justiça restabelece registro de defensivo",
            "Inseticida é utilizado em culturas como soja, milho, algodão e cana-de-açúcar.",
        ),
        ("rice", "Halloween traz drinks", "Receitas combinam a bebida feita de arroz com frutas."),
    ],
)
def test_mentions_that_are_not_about_the_crop(crop, title, summary):
    assert classify(crop, title, summary).about_crop is False


def test_revenue_is_not_a_recipe():
    assert classify("coffee", "Receita de US$ 1 bi com café cai").about_crop is True


def test_summary_only_mention_counts_when_it_says_something_about_the_crop():
    result = classify(
        "orange",
        "Governo prepara diagnóstico de perdas no agro",
        "Estudo aponta alta nos custos da cana-de-açúcar e prejuízos na citricultura e no amendoim.",
    )

    assert result.about_crop is True
    assert result.negative == ("prejuízos",)


def test_title_mention_counts_without_any_signal():
    result = classify("coffee", "Café no Paraná")

    assert (result.about_crop, result.sentiment) == (True, "neutral")
