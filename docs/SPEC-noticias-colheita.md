# SPEC — Notícias Regionais de Colheita

| Campo | Valor |
| :--- | :--- |
| Status | Rascunho para revisão do time |
| Data | 2026-11-03 |
| Base | `main` @ `fec9890` |
| Documento relacionado | [RELATORIO-estado-atual.md](RELATORIO-estado-atual.md) (estado atual do sistema e inventário de rotas) |

---

## 1. Contexto

Hoje o KiPlanto faz uma coisa: recebe solo (N, P, K) + clima da cidade (Open-Meteo) e devolve a cultura recomendada pelo Random Forest em `model/`. O usuário recebe a recomendação, mas nada sobre o que está acontecendo no campo da região dele: andamento da colheita, quebra de safra, chuva atrasando o plantio, etc.

Esta feature acrescenta uma **segunda fonte de informação, independente do modelo**: um scraper que coleta notícias sobre colheita/safra para a **cidade e o estado** informados, e uma tela no frontend que mostra cada notícia **como um artigo**.

## 2. Objetivos e não-objetivos

**Objetivos**

1. Coletar notícias recentes sobre colheita/safra relacionadas a uma cidade e ao estado dela.
2. Ranquear por relevância (tema agrícola + proximidade geográfica + recência).
3. Expor isso numa rota nova da API, sem alterar o contrato das rotas existentes.
4. No frontend, listar as notícias e abrir cada uma em um layout de artigo (manchete, fonte, data, imagem, resumo, link para a matéria original).

**Não-objetivos (v1)**

- Reproduzir o texto integral das matérias (ver §8, direitos autorais).
- Persistir notícias em banco de dados (cache em memória basta; ver questão em aberto Q3).
- Usar as notícias como entrada do modelo de ML.
- Raspar páginas de busca ou qualquer caminho bloqueado por `robots.txt` (ex.: `/busca/*` do g1, `/rss/` do Google News; ver §4.2).
- Adicionar roteamento por URL no frontend (o app hoje navega por estado `activeTab`; mantemos o padrão).

## 3. Visão geral

```
 Frontend (aba "Notícias da Colheita")
        │  GET /news?city=Tupã&state=SP&days=30&limit=10
        ▼
 routers/news_router.py
        │
        ▼
 services/news/service.py ──► cache (TTL 30 min por cidade/UF/janela)
        │
        ├─► 1. resolve local: get_coordinates(city, state) → cidade, estado, UF   (Open-Meteo, já existe)
        │
        ├─► 2. coleta em paralelo (ThreadPool, timeout 8 s por fonte; cache 15 min por URL de feed)
        │      ├── g1 RSS estadual  (/rss/g1/{uf}/)          ← filtrado por estado na origem
        │      ├── g1 Agronegócios RSS (nacional)
        │      ├── Canal Rural RSS (nacional)
        │      └── Portal do Agronegócio RSS (nacional)
        │
        ├─► 3. normaliza → filtra por data → pontua relevância → descarta irrelevantes
        ├─► 4. deduplica (URL canônica + título normalizado)
        └─► 5. ordena por score desc, data desc → corta em `limit`
```

## 4. Fontes de dados

### 4.1 Fontes adotadas

Todas foram testadas em **2026-11-03**: HTTP 200, itens retornados e `robots.txt` liberando o caminho para `User-agent: *`. Usamos só **feeds RSS**, que existem para distribuição de conteúdo. Não raspamos HTML de páginas de listagem.

| ID (`source_feed`) | URL | Escopo | Itens | Com termo forte* | Imagem | Resumo |
| :--- | :--- | :--- | :-: | :-: | :--- | :--- |
| `g1_estadual` | `https://g1.globo.com/rss/g1/{uf}/` | Estado (notícias gerais) | 100 | SP: 2 · MT: 0 | Sim (`media:content`) | Sim (lead) |
| `g1_agro` | `https://g1.globo.com/rss/g1/economia/agronegocios/` | Nacional, agro | 100 | 29 | Sim | Sim |
| `canal_rural` | `https://www.canalrural.com.br/feed/` | Nacional, agro | 10 | 1 | Sim (`<img>` na descrição) | Sim |
| `portal_agronegocio` | `https://www.portaldoagronegocio.com.br/feed` | Nacional, agro | 30 | 6 | Sim (`<image><url>` dentro do `<item>`)† | Sim |
| `globo_rural` | `https://globorural.globo.com/rss/globorural/` | Nacional, agro (cobre ~5 dias) | 100 | não medido | Sim | Sim (lead) |
| `compre_rural` | `https://www.comprerural.com/feed/`; com `crop`, `/wp-json/wp/v2/posts?search=` | Nacional, agro | 10 no feed; até 50 na busca | não medido | Sim (`yoast_head_json.og_image`) | Sim |

\* Itens com `colheita`, `safra`, `plantio` ou `semeadura` no título ou resumo, contados no momento do teste. Todas as fontes dão link direto para a matéria.
† Na implementação (2026-11-03) o feed já trazia imagem em todos os itens, num `<image><url>` fora do padrão RSS. O feedparser expõe isso como `entry.href`.

Observações que afetam a implementação:

- **Cobertura por cidade é o ponto fraco.** Nenhuma fonte permite busca por cidade; a localidade vem do texto (§5.4) ou do feed estadual. No teste, o feed do g1 MT não tinha nenhuma notícia de colheita entre as 100 mais recentes. Os feeds **regionais** do g1 (ex.: `/rss/g1/sp/presidente-prudente-regiao/`, `/rss/g1/sp/bauru-marilia/`, todos com 100 itens) aumentam a precisão e entram como P1 (§10).
- **g1 estadual:** validado para SP, MT, PR, GO, MS, RS, MG e BA; as outras 19 UFs precisam ser validadas na implementação. **Um feed inexistente responde HTTP 200 com 0 itens** (testado com `/rss/g1/xx/`), então "0 itens" conta como falha (`ok=false`, `error="feed vazio ou inexistente"`). O feed é de notícias gerais (polícia, trânsito…) e inclui **publieditorial**: descartar URLs com `/especial-publicitario/`.
- **Canal Rural:** a descrição começa com a legenda da foto (`Foto: Pixabay`) e termina com o rodapé do WordPress (`O post … apareceu primeiro em Canal Rural.`). Remover os dois antes de gerar o `summary`.
- **Feeds nacionais** trazem muita notícia de outros países ("colheita nos EUA", "compras da China"). O filtro de localização (§5.4) descarta esses itens.
- Os feeds do g1 vêm com `gzip`. O `requests` descompacta sozinho; com `curl` é preciso usar `--compressed`.

### 4.2 Fontes avaliadas e descartadas

| Fonte | Motivo |
| :--- | :--- |
| Busca do Canal Rural (`/?s=`) | `robots.txt` bloqueia `/?s=` para `User-agent: *`. |
| Portal do Agronegócio (`/feed?s=`) | O parâmetro é ignorado: devolve o feed comum. A API do WordPress responde 404. |
| GDELT DOC API | Testada em 2026-11-04: HTTP 429 mesmo respeitando 1 requisição a cada 5 s, mais de 10 s por resposta e consulta sem resultado. |
| Google News RSS (`news.google.com/rss/search`) | Seria a única com busca por cidade, mas o **`robots.txt` bloqueia `/rss/` para `User-agent: *`** (só libera `/`, `/home`, `/topics/` etc.). Além disso, os links são redirecionamentos via JavaScript, sem imagem nem resumo. |
| Notícias Agrícolas, Agrolink | Nenhum endpoint de feed encontrado (404) |
| NovaCana | Feed instável: 30 itens numa chamada, 0 na seguinte |
| Embrapa, Revista Cultivar | Feed respondeu sem itens |

## 5. Backend

### 5.1 Arquivos

```
services/
├── br_states.py            # NOVO — 27 UFs: {"SP": {"name": "São Paulo", "g1_feed": "sp"}, ...}
├── climate_data_service.py # ALTERADO — get_coordinates retorna state/uf e aceita filtro por estado
└── news/                   # NOVO
    ├── __init__.py
    ├── http.py             # requests.Session com User-Agent, timeout e cache por URL
    ├── sources.py          # um adaptador por fonte: fetch(location) -> list[RawItem]
    ├── relevance.py        # normalização de texto, keywords, score, dedup
    ├── crops.py            # classe do modelo → termos em português (parâmetro crop)
    └── service.py          # get_harvest_news(city, uf, days, limit, crop) — orquestra tudo + cache
schemas/news_schema.py      # NOVO — modelos Pydantic de resposta
routers/news_router.py      # NOVO — APIRouter(prefix="/news", tags=["Notícias"])
main.py                     # ALTERADO — include_router(news_router) + lista de endpoints em "/"
requirements.txt            # ALTERADO — feedparser, beautifulsoup4
.env.example                # ALTERADO — variáveis da §5.8
```

### 5.2 Resolução da localização (alteração em `get_coordinates`) — **implementada**

O serviço original pegava o primeiro resultado da geocodificação e descartava o estado. Para notícias o estado é indispensável, e há cidades homônimas (testado: "Tupã" existe em SP e no PA; "São José" retorna SC primeiro).

A API Open-Meteo já devolve o estado no campo `admin1` (ex.: `"São Paulo"`). Já implementado, como correção do P-11 do relatório:

```python
def get_coordinates(city: str, country_code: str = "BR", state: Optional[str] = None) -> dict:
    # count=10; retorno: chaves antigas + "state" (nome canônico) + "uf" (None se o admin1 não mapear)
    # levanta CityNotFoundError (subclasse de ValueError) ou ClimateProviderError (falha do Open-Meteo)
```

Só se **acrescentaram** chaves (`state`, `uf`). O geocodificador faz busca aproximada ("Tupã" + RS devolvia "Tuparendi"). Por isso a regra implementada é:
- **com** `state`, só aceita nome idêntico ao pedido (ignorando acentos e caixa); senão, `CityNotFoundError`;
- **sem** `state`, prefere o nome idêntico e cai no resultado mais relevante.

`services/br_states.py` traz as 27 UFs (`BR_STATES`, com `g1_feed`) e `normalize_uf()`, que aceita sigla ou nome.

### 5.3 Pipeline do scraper

1. **Coleta.** Cada adaptador em `sources.py` baixa o feed com `requests` (timeout de 8 s, User-Agent próprio) e passa os bytes para `feedparser.parse()`. Não usar o fetch interno do feedparser, que não aceita timeout. As fontes rodam em paralelo com `concurrent.futures.ThreadPoolExecutor`, no mesmo estilo síncrono do resto do projeto.
2. **Normalização para `RawItem`:** `title`, `summary` (texto puro: `BeautifulSoup(html, "html.parser").get_text(" ", strip=True)`, sem legenda de foto nem rodapé de WordPress (§4.1), cortado em 500 caracteres no limite de palavra), `url`, `source_name`, `source_feed`, `published_at` (UTC), `image_url` (`media:content` ou primeira `<img>` da descrição). Descartar publieditorial (`/especial-publicitario/`).
3. **Filtro de data:** descartar itens com `published_at` mais antigo que `days`. Itens sem data entram com penalidade de recência zero.
4. **Score de relevância** (§5.4). Descartar o que não passar no corte.
5. **Deduplicação:** chave 1 é a URL canônica (sem query string nem fragmento); chave 2 é o título normalizado (minúsculas, sem acento, sem pontuação). Isso cobre a mesma matéria do g1 aparecendo no feed estadual e no de agronegócios. Em caso de duplicata, manter o item que tem imagem e o maior `location_match`.
6. **Ordenação** por `relevance_score` desc, depois `published_at` desc, e corte em `limit`.

### 5.4 Regras de relevância

Texto analisado: `title + " " + summary`, normalizado (minúsculas, sem acentos via `unicodedata.normalize("NFKD", ...)`).

**Tema (harvest_score, teto 6)**

| Peso | Termos |
| :--- | :--- |
| 3 | `colheita`, `safra`, `plantio`, `semeadura`, `quebra de safra` |
| 1 | `lavoura`, `produtividade`, `sacas`, `hectares`, `estiagem`, `geada`, `conab`, `soja`, `milho`, `cana`, `cafe`, `trigo`, `algodao`, `feijao`, `arroz`, `laranja`, `amendoim`, `mandioca` |

Casar por palavra inteira (`\b...\b`) para não pegar falsos positivos como "canal" em `cana`.

**Localização (location_score)**

| `location_match` | Regra | Pontos |
| :--- | :--- | :--- |
| `city` | nome da cidade (normalizado) aparece no texto | +5 |
| `state` | nome do estado ou a UF como palavra isolada aparece no texto | +3 |
| `inferred` | sem menção explícita, mas o item veio de fonte já filtrada pelo local (`g1_estadual`; na P1, também os feeds regionais do g1) | +1 |
| — | fonte nacional sem menção ao local | **descartado** |

**Cuidados ao casar localidade.** Diferente dos termos de tema, a localidade é comparada no **texto original**, com caixa e acentos, como palavra inteira. Normalizar aqui gera falsos positivos:

- UF só casa em maiúsculas, como token isolado (`SP`, `(SP)`, `/SP`, `- SP`). Em minúsculas, `SE`, `PA`, `MA`, `TO`, `AM`, `ES` viram palavras comuns ("se", "para", "ma", "to", "am", "es").
- Nome de estado com acento e inicial maiúscula: `Pará` normalizado vira a preposição "para".
- Nome de cidade com inicial maiúscula. Há municípios que são palavras comuns: Sorriso (MT), Bonito (MS), Formosa (GO), Palmas (TO), Natal (RN).
- `Mato Grosso` não pode casar dentro de `Mato Grosso do Sul`; usar lookahead negativo `(?! do Sul)`.

**Recência:** +2 se ≤ 7 dias; +1 se ≤ 30 dias.

**Corte:** manter só itens com `harvest_score ≥ 3` (pelo menos um termo forte ou três termos fracos) **e** `location_match` definido.
`relevance_score = harvest_score + location_score + recency_score` (máximo 13).

`matched_keywords` lista os termos encontrados; o frontend usa isso no box "Por que você está vendo isto".

### 5.5 Contrato da API

#### `GET /news` (MVP)

| Query param | Tipo | Regra | Default |
| :--- | :--- | :--- | :--- |
| `city` | string | obrigatório, 2–80 caracteres | — |
| `state` | string | opcional; UF de 2 letras, validada contra as 27 UFs | resolvido pela geocodificação |
| `days` | int | 1–180 | 30 |
| `limit` | int | 1–30 | 10 |
| `crop` | string | opcional; classe do modelo (`GET /ai/crops`, ex.: `maize`); desconhecida → 422 | — |

**`crop` junta o modelo às notícias.** `services/news/crops.py` traduz a classe para termos em português (`maize` → `milho`; `coffee` → `café`, `cafeicultura`…). Os termos são casados no texto em minúsculas **com acento**: "romã" não casa com "Roma". As notícias que citam a cultura ganham **+3** (`crop_match: true`) e o máximo de `relevance_score` passa a 16. Em fontes com busca (`compre_rural`), `crop` consulta pelo primeiro termo da cultura, que vem de `CROPS`, nunca de texto do cliente. A ordem é por faixa: cultura na região, cultura em outras regiões e, por último, as demais notícias de colheita da região. Em fonte especializada, citar a cultura dispensa o corte da §5.4; sem menção ao local, o item entra com `location_match: "outside"` (no máximo 10). No feed geral do g1 o corte não muda. `crop` entra na chave do cache de resposta. Um teste garante que toda classe de `model.classes_` tem termos.

Resposta `200`:

```json
{
  "location": { "city": "Tupã", "state": "São Paulo", "uf": "SP" },
  "generated_at": "2026-11-03T17:20:00Z",
  "cached": false,
  "total": 1,
  "crop": null,
  "articles": [
    {
      "id": "3f9a1c2b7d4e8f01",
      "title": "Chuvas podem reduzir safra de trigo de SP a menos de 20% do previsto",
      "summary": "Precipitações em setembro prejudicaram a produção e a qualidade dos grãos; setor defende maior integração entre produtores e indústria moageira",
      "url": "https://www.canalrural.com.br/agricultura/trigo/chuvas-podem-reduzir-safra-de-trigo-de-sp-a-menos-de-20-do-previsto/",
      "source_name": "Canal Rural",
      "source_feed": "canal_rural",
      "published_at": "2026-11-03T14:25:38Z",
      "image_url": "https://imagens-cdn.canalrural.com.br/...",
      "location_match": "state",
      "matched_keywords": ["safra", "trigo"],
      "crop_match": false,
      "relevance_score": 9
    }
  ],
  "sources": [
    { "source": "g1_estadual",        "ok": true,  "items_fetched": 100, "items_kept": 0, "cached": true,  "error": null },
    { "source": "g1_agro",            "ok": true,  "items_fetched": 100, "items_kept": 0, "cached": false, "error": null },
    { "source": "canal_rural",        "ok": true,  "items_fetched": 10,  "items_kept": 1, "cached": false, "error": null },
    { "source": "portal_agronegocio", "ok": false, "items_fetched": 0,   "items_kept": 0, "cached": false, "error": "timeout após 8s" }
  ]
}
```

O artigo do exemplo é um item real do feed do Canal Rural em 2026-11-03. O `summary` já está sem a legenda "Foto: Pixabay" e sem o rodapé do WordPress. `id`, a URL da imagem e o bloco `sources` são ilustrativos. O score segue a §5.4: tema 3 (`safra`) + 1 (`trigo`) = 4; local `state` (token `SP` no título) = 3; recência ≤ 7 dias = 2; total 9.

| Situação | Status | Corpo |
| :--- | :--- | :--- |
| Sucesso, mesmo que parcial (≥1 fonte ok) | 200 | como acima; fontes com falha aparecem em `sources[].ok=false` |
| Sucesso sem notícia relevante | 200 | `articles: []`, `total: 0` |
| Cidade não encontrada (ou não encontrada na UF) | 404 | `{"detail": "Não foi possível localizar 'X': ..."}`, mesmo padrão de `/ai/*` |
| Parâmetro inválido (UF inexistente, `days` > 180...) | 422 | validação padrão do FastAPI |
| Geocodificação indisponível (falha do Open-Meteo) | 502 | `{"detail": ...}`, mesmo padrão de `/ai/*` |
| **Todas** as fontes falharam | 502 | `{"detail": "Nenhuma fonte de notícias respondeu", "sources": [...]}` |

#### `GET /news/{article_id}` (P1, opcional)

Devolve um artigo do cache, enriquecido com `author` e `og:image`/`og:description` de melhor qualidade, buscados **uma vez** na página original e guardados em cache por 24 h. O enriquecimento só acontece para URLs que **vieram dos nossos próprios feeds** e cujo domínio está na allowlist (`g1.globo.com`, `www.canalrural.com.br`, `www.portaldoagronegocio.com.br`; este último é o que mais ganha, porque o feed não traz imagem). A rota nunca recebe URL do cliente (proteção contra SSRF). Retorna `404` se o id não estiver mais em cache; o frontend então recarrega a lista. O MVP não precisa desta rota, porque o artigo é renderizado com os dados da lista.

### 5.6 Schemas (`schemas/news_schema.py`)

```python
SourceFeed = Literal["g1_estadual", "g1_agro", "canal_rural", "portal_agronegocio"]

class NewsLocation(BaseModel):
    city: str
    state: Optional[str] = None
    uf: Optional[str] = None

class NewsCrop(BaseModel):              # presente quando `crop` é informado
    id: str                              # classe do modelo, ex.: "maize"
    name: str                            # "Milho"
    terms: List[str]                     # termos procurados nas notícias

class NewsArticle(BaseModel):
    id: str                              # sha1(url canônica)[:16]
    title: str
    summary: Optional[str] = None        # texto puro, ≤ 500 caracteres
    url: str                             # http(s) apenas (validar o esquema)
    source_name: str
    source_feed: SourceFeed
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None      # http(s) apenas
    location_match: Literal["city", "state", "inferred"]
    matched_keywords: List[str]          # tema + termos da cultura encontrados
    crop_match: bool = False             # cita a cultura pedida em `crop`
    relevance_score: float

class SourceStatus(BaseModel):
    source: SourceFeed
    ok: bool
    items_fetched: int
    items_kept: int
    cached: bool
    error: Optional[str] = None

class NewsResponse(BaseModel):
    location: NewsLocation
    generated_at: datetime
    cached: bool
    total: int
    crop: Optional[NewsCrop] = None
    articles: List[NewsArticle]
    sources: List[SourceStatus]
```

### 5.7 Cache, desempenho e etiqueta de coleta

- **Cache de resposta:** chave `(cidade normalizada, UF, days)`, TTL de 30 min. Um cache hit deve responder em menos de 300 ms.
- **Cache por URL de feed:** TTL de 15 min. Cidades do mesmo estado reaproveitam o mesmo download do g1 estadual, e cada feed é baixado no máximo 4 vezes por hora por processo.
- Implementação: `dict` + `threading.Lock` + timestamp, sem dependência nova. O cache é por processo; com `--reload` ou vários workers cada um tem o seu, o que é aceitável para o projeto.
- **User-Agent:** `KiPlantoBot/1.0 (+https://github.com/AndreasTBerti/KiPlanto; projeto academico)`. Identificável e com contato.
- Nada de rotação de User-Agent, proxy ou qualquer forma de contornar bloqueio. Se uma fonte responder 403 ou 429, marcar `ok=false` e seguir.
- Tempo máximo de uma requisição sem cache: cerca de 10 s (geocodificação ~2 s + fontes em paralelo, até 8 s).

### 5.8 Configuração (`.env.example`)

```
NEWS_CACHE_TTL_SECONDS=1800
NEWS_FEED_CACHE_TTL_SECONDS=900
NEWS_HTTP_TIMEOUT_SECONDS=8
NEWS_ENABLED_SOURCES=g1_estadual,g1_agro,canal_rural,portal_agronegocio,globo_rural,compre_rural
```

### 5.9 Dependências novas

```
feedparser>=6.0
beautifulsoup4>=4.12
```

Usar o parser `html.parser`, que já vem com o Python. `lxml` não é necessário e evita dependência compilada no Windows.

### 5.10 Segurança

- **SSRF:** o backend só baixa URLs fixas de feed (constantes no código) e, na P1, URLs que vieram desses feeds e estão na allowlist. Nenhum parâmetro do cliente vira URL.
- **XSS:** `summary` sai do backend como texto puro, e o frontend renderiza como texto. **Proibido usar `dangerouslySetInnerHTML`.** `url` e `image_url` só são aceitos com esquema `http`/`https`, para descartar `javascript:` e similares.
- Links externos abrem com `target="_blank" rel="noopener noreferrer"`. Imagens carregam com `referrerPolicy="no-referrer"` e `loading="lazy"`.

## 6. Frontend

### 6.1 Arquivos

```
src/types/api.ts                       # ALTERADO — NewsArticle, NewsResponse, SourceStatus, NewsLocation
src/services/api.ts                    # ALTERADO — getHarvestNews({ city, state?, days?, limit?, crop? })
src/components/Sidebar.tsx             # ALTERADO — NavTab += 'news'; item "Notícias da Colheita" (ícone Newspaper)
src/components/Header.tsx              # ALTERADO — TAB_TITLES.news
src/App.tsx                            # ALTERADO — renderiza <NewsView />
src/components/views/NewsView.tsx      # NOVO — busca + lista de cards + controle do artigo aberto
src/components/news/NewsCard.tsx       # NOVO — card da lista
src/components/news/ArticleView.tsx    # NOVO — leitura em formato de artigo
src/components/news/RegionalNewsCard.tsx # NOVO — notícias da região cruzadas com o modelo, na Recomendação (§6.4)
src/components/news/NewsImage.tsx      # NOVO — imagem lazy, sem Referer, com fallback em erro
src/components/news/newsUtils.ts       # NOVO — datas pt-BR, badges, "por que você está vendo isto", NewsIntent
src/constants/cities.ts                # NOVO — move COMMON_CITIES de PredictionView para reuso
vite.config.ts                         # ALTERADO — proxy '/news' (consistência; ver relatório P-09)
```

Os ícones `Newspaper`, `ExternalLink`, `ArrowLeft`, `CalendarDays` e `MapPin` existem no `lucide-react@1.48.0` instalado, então não entra dependência nova no frontend.

### 6.2 Tela de lista (`NewsView`)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [📍 Tupã                         ] [UF: SP ▾] [Últimos 30 dias ▾] [Buscar] │
│  Tupã · Campinas · Ribeirão Preto · Londrina · Uberlândia · Sorriso ...   │
└──────────────────────────────────────────────────────────────────────────┘
 Notícias de colheita · Tupã, São Paulo                      8 resultados

┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│ [ imagem 16:9       ] │ │ [ imagem 16:9       ] │ │ [   sem imagem:     ] │
│ Fonte · há 2 dias     │ │ Fonte · 21 out        │ │ [ ícone Newspaper  ] │
│ Manchete da notícia   │ │ Manchete da notícia   │ │ Fonte · 12 out        │
│ em até 2 linhas...    │ │ em até 2 linhas...    │ │ Manchete em 2 linhas  │
│ resumo em 3 linhas... │ │ resumo em 3 linhas... │ │ resumo em 3 linhas... │
│ [SP] colheita · cana  │ │ [Tupã] safra          │ │ [Região] safra        │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘

 Fontes: 3 de 4 responderam (Canal Rural indisponível)
```

- Grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, mesmo visual dos outros cards (`bg-slate-900/80 border-slate-800 rounded-xl`), destaque em **âmbar** para diferenciar das telas de modelo (esmeralda).
- O card inteiro é um `<button>` acessível que abre o artigo. Título limitado a 2 linhas (`line-clamp-2`), resumo a 3.
- Badge de localização: `city` mostra o nome da cidade, `state` mostra a UF, `inferred` mostra "Região".
- Busca inicial automática com `Tupã`/`SP`, o mesmo default da tela de clima.
- **Estados:** loading com 3 cards *skeleton*; vazio com "Nenhuma notícia de colheita para Tupã/SP nos últimos 30 dias" e botão **"Ampliar para 90 dias"**; erro no box rosa padrão do app; parcial com rodapé "X de 4 fontes responderam".

### 6.3 Tela de artigo (`ArticleView`)

```
 ← Voltar às notícias

 FONTE · SÃO PAULO · 21 DE OUTUBRO DE 2026                       [SP]
 ═══════════════════════════════════════════════════════════════════
 Manchete da notícia em tipografia grande,
 quebrando em até três linhas                               (h1, 3xl)

 ┌───────────────────────────────────────────────────────────────┐
 │                       imagem de capa                          │
 └───────────────────────────────────────────────────────────────┘
  Imagem: Fonte

 Resumo publicado no feed do veículo, exibido como lead do      (lead,
 artigo, até 500 caracteres...                                   text-lg)

 ┌ Por que você está vendo isto ────────────────────────────────┐
 │ Menciona São Paulo · termos: colheita, safra, cana            │
 └───────────────────────────────────────────────────────────────┘

 [ Ler matéria completa em Fonte ↗ ]

 Conteúdo de terceiros. O KiPlanto exibe apenas título e resumo
 publicados no feed do veículo; todos os direitos pertencem a ele.
```

- Coluna de leitura centralizada (`max-w-3xl`) com tipografia de artigo: *kicker* em caixa alta (fonte · data longa em pt-BR · local), `h1` grande, imagem com crédito, lead em corpo maior, metadados em `<time dateTime=...>`.
- Sem imagem: omitir o bloco (não mostrar placeholder grande). Se a imagem falhar ao carregar (`onError`), esconder o bloco.
- O Portal do Agronegócio não envia imagem; o artigo começa direto no lead. Se algum item vier sem resumo, mostrar manchete, fonte, data e CTA, com a nota "Resumo indisponível nesta fonte".
- O artigo aberto é estado local do `NewsView` (`selectedArticle`). "Voltar" volta para a lista **sem refazer a requisição** e restaura a rolagem. Ao abrir, rolar para o topo.

### 6.4 Integração com a Recomendação de Safra — **implementada na v1** (ver Q2)

Depois que `PredictionView` mostra o resultado, exibir um card compacto **"Colheita na região de {cidade}"** com as 3 manchetes mais relevantes, buscadas em paralelo e sem bloquear a recomendação. Clicar numa manchete leva à aba de notícias com o artigo aberto. Isso exige subir `activeTab` e o artigo selecionado para o `App` (ou um callback `onOpenArticle`).

Como ficou: ao sair a análise, o card chama `GET /news?city&state&crop=<cultura recomendada>` com a cidade e a UF resolvidas pela recomendação e informa se há notícias da cultura na região. Sem nenhuma, avisa e mostra o mais próximo, com o badge "Outras regiões". A aba de notícias, aberta pela sidebar, usa a região e a cultura da última análise do histórico. O `App` guarda um `newsIntent` ({ query, response, articleId }) e o `NewsView` abre direto no artigo, **reaproveitando a resposta do card, sem nova requisição**. Na aba de notícias, o select de cultura faz o mesmo manualmente. O município é escolhido na lista do IBGE (`frontend/src/constants/municipios.json`, gerada por `scripts/gerar_municipios.py`).

**Atualização (recomendação cruzada):** o card deixou de ser compacto e passou para o topo da coluna de resultado, com a notícia principal em destaque (imagem, título e resumo). Ele agora chama `POST /ai/cross-recommendation`, que busca as notícias de até 3 culturas candidatas e aplica a regra de `services/cross_recommendation.py`, descrita no README. Com isso, o texto acima sobre `GET /news` no card e as "3 manchetes" ficam substituídos; o restante continua valendo.

## 7. Testes

Backend com `pytest`, **sem rede**, usando fixtures. Dependências de desenvolvimento em `requirements-dev.txt` (`pytest`, `httpx` para o `TestClient`).

| Arquivo | O que cobre |
| :--- | :--- |
| `tests/fixtures/news/*.xml` | Amostras reais salvas de cada feed (g1 estadual, g1 agro, Canal Rural, Portal do Agronegócio) e um feed vazio |
| `tests/test_news_relevance.py` | normalização sem acentos; palavra inteira (`canal` ≠ `cana`); score; corte; `location_match` city/state/inferred/descartado; casos negativos de localidade ("se"≠SE, "para"≠Pará, "sorriso"≠Sorriso, "Mato Grosso do Sul"≠MT); dedup que prefere imagem e melhor `location_match`; bônus da cultura (`crop`) e mapa que cobre todas as classes do modelo |
| `tests/test_news_sources.py` | parse de cada fixture: imagem extraída do `media:content` (g1) e do `<img>` (Canal Rural); legenda "Foto: …" e rodapé "O post … apareceu primeiro em …" removidos; publieditorial do g1 descartado; resumo sem HTML e ≤ 500 caracteres; feed vazio → `ok=false` |
| `tests/test_news_router.py` | `TestClient` com fontes mockadas: 200 completo; 200 parcial; 502 com todas falhando; 422 para UF, `days`, `limit` ou `crop` inválidos; 404 para cidade inexistente; 502 na falha da geocodificação; segundo request com `cached=true` em < 300 ms; `crop` reordena; fonte lenta vira timeout sem travar a rota |
| `tests/test_climate_service.py` (✅ implementado) | `get_coordinates("São José", state="SC")` escolhe SC; chaves antigas continuam presentes (regressão); com UF, nome aproximado é rejeitado |

Frontend: o projeto não tem framework de testes. Para a v1, `npm run build` e `npm run lint` sem warnings novos, mais o roteiro manual dos critérios CA-09 e CA-10.

## 8. Considerações legais e éticas

- **Direitos autorais (Lei 9.610/98):** exibimos só o que o próprio veículo distribui no feed (título, resumo, imagem de capa), sempre com crédito e link para a matéria original. **Não** armazenamos nem reproduzimos o corpo da matéria.
- **robots.txt:** os 4 feeds adotados estão liberados para `User-agent: *` (verificado em 2026-11-03). O Google News foi descartado justamente por isso (§4.2). **Regra para fontes novas:** só entram se o `robots.txt` liberar o caminho exato; revalidar a cada fonte adicionada.
- **Carga nos servidores:** com o cache de 15 min por feed, o pior caso é ~4 downloads/hora por feed por processo.
- **Transparência:** o box "Por que você está vendo isto" e o aviso de conteúdo de terceiros deixam claro que a seleção é automática.

## 9. Critérios de aceite

| ID | Critério |
| :--- | :--- |
| CA-01 | `GET /news?city=Tupã&state=SP` responde 200 em ≤ 10 s sem cache e ≤ 300 ms com cache (`cached=true`). |
| CA-02 | Todo artigo tem `title`, `url` http(s), `source_name`, `source_feed`, `location_match` e ao menos 1 item em `matched_keywords`. |
| CA-03 | Nenhum artigo tem `published_at` mais antigo que `days`. |
| CA-04 | Com uma fonte fora do ar, a resposta é 200, a fonte aparece com `ok=false` e as demais continuam. |
| CA-05 | Com todas as fontes fora do ar, a resposta é 502. |
| CA-06 | Cidade inexistente retorna 404; UF inválida retorna 422. |
| CA-07 | `city=São José&state=SC` resolve para Santa Catarina; sem `state`, `location` mostra o estado escolhido. |
| CA-08 | `summary` nunca contém tags HTML e tem ≤ 500 caracteres. |
| CA-09 | No frontend, a aba "Notícias da Colheita" aparece na sidebar e no header; a busca lista os cards; o clique abre o artigo; "Voltar" retorna sem nova requisição; o CTA abre a fonte em nova aba com `noopener`. |
| CA-10 | Os estados de loading, vazio (com "Ampliar para 90 dias"), erro e parcial aparecem corretamente. |
| CA-11 | Regressão: `/ai/prevision`, `/ai/prevision/direct`, `/ai/climate/{city}` e `/ai/crops` mantêm o mesmo contrato. |
| CA-12 | `pytest` passa offline; `npm run build` passa; `npm run lint` não introduz warnings novos. |

## 10. Plano de entrega

| # | Tarefa | Prioridade | Tamanho |
| :--- | :--- | :--- | :--- |
| 0 | ✅ Pré-requisitos do relatório: corrigir venv local (P-04) e fixar versão do scikit-learn (P-05) | P0 | P |
| 1 | ✅ `br_states.py` + extensão de `get_coordinates` (state/uf, filtro por UF) + teste de regressão (`tests/test_climate_service.py`) | P0 | P |
| 2 | ✅ `services/news/http.py` + `sources.py` (4 adaptadores) + fixtures | P0 | M |
| 3 | ✅ `relevance.py` (normalização, score, corte, dedup) + testes | P0 | M |
| 4 | ✅ `service.py` (orquestração, paralelismo, caches) + `news_schema.py` + `news_router.py` + testes de rota | P0 | M |
| 5 | ✅ Frontend: tipos, `getHarvestNews`, sidebar/header, `NewsView`, `NewsCard`, `ArticleView` | P0 | M |
| 6 | ✅ README (rotas e módulos), lista de endpoints em `GET /`, `.env.example`, proxy do Vite | P0 | P |
| 7 | Feeds regionais do g1 (mapa cidade → região, começando por SP, PR, MT, GO, MS) para mais precisão por cidade | P1 | M |
| 8 | ✅ Card "Colheita na região" na Recomendação de Safra (§6.4) | P1 | P |
| 9 | `GET /news/{article_id}` com enriquecimento via allowlist | P1 | M |
| 10 | ✅ Parâmetro `crop` para priorizar notícias da cultura recomendada | P2 | P |

Tamanhos: P ≈ até meio período, M ≈ 1 período, G ≈ mais de 1 dia.

**Impacto no número de rotas:** a API passa de 6 rotas de aplicação para **7** no MVP (`GET /news`) e **8** com a P1 (`GET /news/{article_id}`). O frontend passa de 5 para **6** telas.

## 11. Riscos

| Risco | Mitigação |
| :--- | :--- |
| Cidade pequena sem notícia própria; estado com poucas notícias de colheita (g1 MT teve 0 de 100 no teste) | Pontuação por estado e `inferred`; feeds nacionais de agro; estado vazio com "Ampliar para 90 dias" |
| Fonte muda formato ou remove o feed (o g1 responde 200 vazio) | `sources[]` expõe a falha; "0 itens" conta como falha; testes com fixtures pegam mudança de parser |
| Uma fonte responde 403/429 ou fica fora do ar | É uma de 4 fontes; cache por URL; falha parcial não derruba a rota |
| Pouca precisão por cidade sem fonte com busca (Google News descartado por `robots.txt`) | Feeds regionais do g1 na P1; questão Q5 |
| Falsos positivos ("safra de talentos", "colheita nos EUA", publieditorial) | Exigir local + tema; casar palavra inteira; descartar `/especial-publicitario/`; testes com casos negativos; box de transparência |
| Latência alta sem cache | Fontes em paralelo, timeout por fonte, cache de resposta e de feed |

## 12. Questões em aberto para o time

- **Q1.** A janela padrão de 30 dias atende, ou a colheita de culturas de ciclo longo pede 60?
- **Q2.** ~~Vale priorizar notícias da cultura recomendada pelo modelo (P2, item 10) já na v1?~~ **Decidido: sim.** O pedido foi juntar o resultado do modelo com o do scraper. Entraram na v1 o parâmetro `crop` (item 10) e o card da Recomendação (item 8, §6.4). Limitação: várias classes do dataset (juta, feijão-moth, grão-de-bico, lentilha) quase não aparecem na imprensa brasileira, então o bônus raramente dispara para elas.
- **Q3.** Como o projeto é da disciplina de Big Data: queremos **persistir** as notícias coletadas (SQLite/Parquet) para análises futuras, por exemplo sentimento por região × safra? Isso muda a §2 (não-objetivos) e acrescenta um job de coleta periódica.
- **Q4.** Hotlink das imagens dos veículos é aceitável para o projeto, ou preferimos mostrar só o ícone da fonte?
- **Q5.** Se a precisão por cidade com feeds RSS não for suficiente, vale adotar uma **API de notícias com chave** (com termos de uso que permitam o uso) em vez de raspar busca? Isso traria busca por cidade sem violar `robots.txt`, mas acrescenta cadastro e limite de requisições.
