# KiPlanto - Plataforma Agroclimática e Recomendação de Safra

Sistema de recomendação agronômica que combina um modelo de Machine Learning (Random Forest, 22 culturas) com dados meteorológicos do Open-Meteo e a análise de solo (N-P-K).

---

## Estrutura do Projeto

```
KiPlanto/
├── main.py                     # Ponto de entrada FastAPI (CORS configurável por .env)
├── requirements.txt            # Dependências do backend
├── requirements-dev.txt        # + pytest, httpx e ruff (testes e lint)
├── ruff.toml / pytest.ini      # Configuração do lint e dos testes
├── .env.example                # Modelo de variáveis de ambiente do backend
├── model/
│   ├── crop_model.py           # Inferência: 6 features, top 3 e confiança
│   └── modelo_recomendacao_safra.joblib  # Random Forest (scikit-learn 1.6.1)
├── routers/
│   ├── auth_router.py          # /auth (cadastro, login, logout) e a dependência require_user
│   ├── ai_router.py            # /ai/prevision, /ai/prevision/direct, /ai/cross-recommendation, /ai/climate, /ai/crops
│   ├── market_router.py        # /market (preço e produtividade, dados do IBGE)
│   └── news_router.py          # /news (notícias de colheita)
├── schemas/                    # Schemas Pydantic (validação de entrada e saída)
├── services/
│   ├── auth_service.py         # Contas e sessões em SQLite, com senhas em scrypt
│   ├── climate_data_service.py # Open-Meteo: geocodificação, previsão e histórico de chuva (com cache)
│   ├── cross_recommendation.py # Cruza as probabilidades do modelo com as notícias da região
│   ├── cross_report.py         # Report: junta a ordem do modelo com a leitura das notícias
│   ├── llm_reader.py           # IA: classifica as notícias e escreve a conclusão, conferindo as respostas
│   ├── openrouter.py           # Cliente do OpenRouter, com trava de preço e orçamento
│   ├── br_states.py            # As 27 UFs (sigla, nome, feed do g1)
│   ├── municipios_coordenadas.json # Centroide IBGE dos municípios (gerado)
│   └── news/                   # Scraper de notícias de colheita
├── scripts/gerar_municipios.py # Regenera a lista e as coordenadas dos municípios a partir do IBGE
├── tests/                      # Testes automatizados (sem acesso à rede)
├── docs/                       # Relatório do estado do sistema e SPECs
├── .github/workflows/ci.yml    # CI: ruff + pytest e lint + build do frontend
└── frontend/                   # React + TypeScript + Tailwind CSS (Vite)
```

---

## Como Executar

Pré-requisitos: Python 3.10+ (o CI usa 3.13) e Node.js 24.

### 1. Backend (FastAPI)

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env    # opcional: os valores padrão já funcionam
uvicorn main:app --reload --port 8000
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # opcional: os valores padrão já funcionam
uvicorn main:app --reload --port 8000
```

A documentação interativa fica em http://localhost:8000/docs (Swagger) e http://localhost:8000/redoc.

> O `scikit-learn` está fixado em **1.6.1** e o `numpy` em **2.x** porque o modelo `.joblib` foi serializado com essas versões. Outra versão do scikit-learn gera `InconsistentVersionWarning` e pode mudar os resultados.

### 2. Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm install
npm run dev               # http://localhost:3000
```

Em desenvolvimento o frontend chama a API pela mesma origem e o proxy do Vite encaminha `/ai`, `/auth`, `/health`, `/news` e `/market` para `http://localhost:8000`. Para apontar para outro servidor, crie `frontend/.env.local` com `VITE_API_URL=http://servidor:porta` (veja `frontend/.env.example`) e libere a origem do front em `CORS_ALLOW_ORIGINS` no `.env` do backend.

### 3. Testes e lint

```bash
pip install -r requirements-dev.txt
ruff check .              # lint do Python
pytest                    # testes do backend (sem acesso à rede)

cd frontend
npm run lint              # oxlint
npm run build             # checagem de tipos (tsc) + build
```

O workflow `.github/workflows/ci.yml` roda tudo isso a cada push na `main` e em pull requests.

---

## Como o modelo recebe os dados

O modelo usa **6 features**. O pH **não** é uma delas: a API aceita e o histórico registra o pH, mas ele não influencia a recomendação.

| Feature | Unidade | Em `/ai/prevision`, vem de | Faixa que o modelo distingue* |
| :--- | :--- | :--- | :--- |
| `N`, `P`, `K` | mg/kg | Formulário | 0,5–126 · 7–144,5 · 14,5–202,5 |
| `temperature` | °C | Média diária prevista para os próximos 7 dias | 16–37 |
| `humidity` | % | Média diária prevista para os próximos 7 dias | 18–96 |
| `rainfall` | mm/mês | Chuva média mensal dos últimos 12 meses (histórico ERA5 do Open-Meteo) | 30–265 |

\* Menor e maior limiar de corte entre as 100 árvores. Valores fora da faixa são aceitos, mas o modelo trata todos como o extremo mais próximo.

A resposta de `/ai/prevision` traz em `features` os valores exatos entregues ao modelo, e a tela de Recomendação os exibe no card "Entradas do Modelo".

---

## Rotas da API

| Método | Rota | Descrição | Erros |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Status da API e lista de endpoints | — |
| `GET` | `/health` | Verificação de integridade | — |
| `POST` | `/auth/register` | Cria uma conta e inicia a sessão. Corpo: `name`, `email`, `password` (8 a 128 caracteres) | 409 e-mail já cadastrado · 422 entrada inválida · 429 muitos cadastros |
| `POST` | `/auth/login` | Inicia uma sessão. Corpo: `email`, `password`. Devolve `token` e `user` | 401 e-mail ou senha incorretos · 429 após 5 tentativas em 15 min |
| `POST` | `/auth/logout` | Encerra a sessão atual | 401 sem sessão válida |
| `GET` | `/auth/me` | A conta da sessão atual | 401 sem sessão válida |
| `POST` | `/ai/prevision` | Recomendação por município e solo. Corpo: `city`, `state` (UF, opcional na API; o frontend sempre envia), `n_ratio`, `p_ratio`, `k_ratio`, `ph` (opcional, não usado) | 404 cidade não encontrada · 422 entrada inválida · 502 Open-Meteo indisponível |
| `POST` | `/ai/prevision/direct` | Simulação com as 6 features informadas. Corpo: `n`, `p`, `k`, `temperature`, `humidity`, `rainfall` (mm/mês), `ph` (opcional, não usado) | 422 entrada inválida |
| `POST` | `/ai/cross-recommendation` | Cruza o modelo com as notícias da região. Corpo: `city`, `state` (UF, opcional) e as 6 features de `/ai/prevision/direct`. Falha nas notícias não é erro: a resposta mantém a ordem do modelo | 404 cidade não encontrada · 422 entrada inválida |
| `GET` | `/ai/climate/{city}?state=UF` | Condições atuais, médias de 7 dias e chuva média mensal | 404 · 422 · 502 |
| `GET` | `/ai/crops` | As 22 culturas que o modelo conhece | 500 se o modelo não carregar |
| `GET` | `/news?city=&state=&days=&limit=&crop=` | Notícias de colheita da cidade/estado, ranqueadas por relevância. `city` (2–80 caracteres), `state` (UF, opcional), `days` (1–180, padrão 30), `limit` (1–30, padrão 10), `crop` (classe de `/ai/crops`, opcional: busca a cultura indicada, primeiro na região e depois em outras regiões, com `location_match: "outside"`) | 404 cidade não encontrada · 422 parâmetro inválido · 502 todas as fontes ou a geocodificação falharam |
| `GET` | `/market?crop=&city=&state=` | Preço recebido, produção por hectare, receita bruta, área colhida e produção total de uma cultura, no município, no estado e no Brasil. Dados anuais do IBGE (PAM, tabela 5457): o preço é o valor da produção dividido pela quantidade, não a cotação do dia. `crop` (classe de `/ai/crops`), `city` e `state` opcionais. Grão-de-bico, lentilha, guandu e romã não têm dado no IBGE, e as variedades de feijão usam o dado geral de feijão | 422 parâmetro inválido · 502 IBGE indisponível |
| `GET` | `/docs`, `/redoc`, `/openapi.json` | Documentação gerada pelo FastAPI | — |

**`state` (UF):** resolve cidades com o mesmo nome em estados diferentes (ex.: Cascavel/PR e Cascavel/CE). Com UF, o nome da cidade precisa bater exatamente (acentos e maiúsculas não importam); sem UF, vale o resultado mais relevante do geocodificador. As respostas trazem `city`, `state` e `uf` resolvidos.

**Validação:** valores fisicamente impossíveis são rejeitados com 422 (nutrientes negativos, umidade fora de 0–100, pH fora de 0–14, chuva negativa, UF inexistente).

### Campos obsoletos

Mantidos nas respostas por compatibilidade. Serão removidos numa versão futura:

| Campo antigo | Use no lugar | Observação |
| :--- | :--- | :--- |
| `crop_recomendation` | `crop_recommendation` | Grafia corrigida |
| `climate_data.temperature_forecast` | `temperature_mean_7d` | Mesmo valor |
| `climate_data.preciptation_forecast` | `precipitation_total_7d` ou `rainfall_monthly_avg` | O campo antigo é a **média diária** dos 7 dias, não o total |
| `climate_data.rain_forecast` | — | Média diária de chuva dos 7 dias |

---

## Contas e login

As rotas de `/ai`, `/news` e `/market` exigem o cabeçalho `Authorization: Bearer <token>`; sem ele, respondem 401. O token vem de `/auth/register` ou `/auth/login` e vale por 7 dias. No Swagger (`/docs`), use o botão **Authorize**.

As contas ficam em SQLite, em `data/kiplanto.db` (fora do git). A senha é guardada só como hash scrypt com sal, e o banco guarda só o hash do token da sessão. No navegador, o token fica no `localStorage`, e o histórico de análises é separado por conta, mas continua sendo guardado só naquele navegador.

Limites conhecidos: o cadastro é aberto a qualquer pessoa, não há confirmação de e-mail nem recuperação de senha, e o limite de tentativas fica em memória, por processo.

---

## Variáveis de ambiente

Backend (`.env` na raiz; todas opcionais):

| Variável | Padrão | Uso |
| :--- | :--- | :--- |
| `OPEN_METEO_URL` | `https://api.open-meteo.com/v1/forecast` | Previsão do tempo |
| `GEO_ENCODING_URL` | `https://geocoding-api.open-meteo.com/v1/search` | Geocodificação |
| `OPEN_METEO_ARCHIVE_URL` | `https://archive-api.open-meteo.com/v1/archive` | Histórico de chuva (12 meses) |
| `CLIMATE_HTTP_TIMEOUT_SECONDS` | `10` | Timeout das chamadas ao Open-Meteo |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,…:4173` | Origens liberadas no CORS, separadas por vírgula |
| `NEWS_CACHE_TTL_SECONDS` | `1800` | Cache da resposta de `/news` por cidade/UF/janela/cultura (resposta parcial: até 2 min) |
| `NEWS_FEED_CACHE_TTL_SECONDS` | `900` | Cache de cada feed RSS baixado |
| `NEWS_HTTP_TIMEOUT_SECONDS` | `8` | Timeout por fonte de notícias |
| `NEWS_ENABLED_SOURCES` | todas | Fontes ativas: `g1_estadual,g1_agro,canal_rural,portal_agronegocio,globo_rural,compre_rural` |

Frontend (`frontend/.env.local`):

| Variável | Padrão | Uso |
| :--- | :--- | :--- |
| `VITE_API_URL` | vazio (mesma origem + proxy do Vite) | URL da API |

---

## Módulos do Frontend

- **Recomendação de Safra**: UF e município escolhidos na lista oficial do IBGE, nutrientes N-P-K e recomendação com probabilidades. Ao gerar a análise, o formulário dá lugar aos resultados, e **"Fazer outra análise"** traz o formulário de volta com os mesmos valores. A tela mostra as entradas exatas do modelo e, à parte, as condições atuais do clima. O pH é registrado no histórico, mas não é usado pelo modelo. Abaixo da predição, o card **"Preço e produtividade"** traz os dados do IBGE para a cultura indicada, comparando município, estado e Brasil. Ao lado, o card de notícias busca a cultura indicada naquela região; quando não há nada sobre ela na região, o card avisa e mostra o mais próximo. Clicar numa manchete abre o artigo na aba de notícias.
- **Notícias da Colheita**: abre com a região e a cultura da última análise (sem análise, convida a fazer uma); os filtros de município, período e cultura permitem outra busca. Cada notícia vira um card e abre em formato de artigo (manchete, fonte, data, imagem, resumo, motivo da seleção e link para a matéria original).
- **Simulação Direta**: ajuste das 6 variáveis do modelo (chuva em mm/mês) com recálculo em tempo real.
- **Consulta Climática**: condições atuais, médias e total previstos para 7 dias e chuva média mensal dos últimos 12 meses.
- **Catálogo de Culturas**: as 22 culturas com filtros por categoria, conferidas com `/ai/crops` (avisa se catálogo e modelo divergirem).
- **Histórico de Análises**: registro das últimas 50 análises no navegador, com detalhamento e exportação para JSON.

---

## Notícias de colheita

Segunda fonte de informação, independente do modelo, mas ligada ao resultado dele:

1. **Coleta** (`services/news/sources.py`): baixada em paralelo, com timeout por fonte e User-Agent identificável. São feeds RSS do g1 do estado (`/rss/g1/{uf}/`), g1 Agronegócios, Canal Rural, Portal do Agronegócio e Globo Rural, mais a Compre Rural, que com `crop` é consultada pela cultura na API de busca do WordPress. Publieditoriais do g1 são descartados.
2. **Relevância** (`services/news/relevance.py`): tema (colheita, safra, plantio…), localidade (cidade +5, estado/UF +3, feed estadual +1) e recência. Fica só o que fala de colheita **e** da região. Nomes de lugares são comparados com acento e maiúscula, então "para" não vira Pará e "sorriso" não vira Sorriso (MT).
3. **Modelo + notícias** (`services/news/crops.py`): `crop=maize` traduz a classe do modelo para termos em português ("milho"). A ordem passa a ser: cultura na região, cultura em outras regiões (`location_match: "outside"`, no máximo 10) e demais notícias de colheita da região. Em veículo especializado, citar a cultura dispensa o corte de tema; no feed geral do g1, não, porque "manga" pode ser de camisa.
4. **Cache**: resposta por 30 min e cada feed por 15 min, em memória, por processo. A resposta traz em `sources[]` o status de cada fonte; se uma fonte cair, as outras continuam.
5. **Classificador** (`services/llm_reader.py`, com reserva em `services/news/classifier.py`): um modelo barato via OpenRouter lê as notícias, em lotes, e o que ele não responder fica com regras locais em português, que não usam rede nem chave. Para cada notícia e cultura, responde se a notícia é mesmo da cultura ("alerta laranja", "Festa da Uva" e "culturas como soja, milho, algodão" não são) e se é `positive`, `negative`, `mixed` ou `neutral` do ponto de vista de quem produz: preço em alta é bom, custo em alta é ruim. O sentimento é por cultura: em "Soja sobe, milho cai", cada uma recebe o seu. `signals` mostra as palavras que decidiram, e a IA só pode citar palavras que existem na notícia.
6. **Recomendação cruzada** (`services/cross_recommendation.py`): sem nota ponderada. As candidatas são sempre as 3 primeiras do modelo, as mesmas da tela (acima de 1%). Só muda a ordem quem tem pelo menos 10% e fica a até 10 pontos da primeira: a que tem notícia da região sobre a cultura, sem saldo desfavorável, passa à frente da que não tem, e conta só ter ou não ter, não a quantidade. Termos de risco (geada, estiagem, praga…) também geram alerta. Citar só "feijão" não muda a ordem, porque o termo vale para 5 classes do modelo. Se a busca falhar para alguma candidata, vale a ordem do modelo. A tela mostra o card no topo da coluna de resultado e mantém a indicação original do modelo logo abaixo. O histórico e a aba de notícias continuam usando a indicação do modelo.
7. **Report** (`services/cross_report.py`): junta as duas leituras. Para cada candidata, na ordem do modelo, traz a probabilidade, a leitura das notícias e as manchetes; no fim, uma conclusão como "Banana (60%) lidera no modelo, mas as notícias são desfavoráveis. Laranja (12%) tem notícias favoráveis, mas o modelo a considera menos adequada ao solo e ao clima: avalie antes de trocar." A região tem prioridade; as outras regiões valem quando a região não traz sinal claro. Quem escreve a conclusão é a IA, e o texto só é aceito se citar a primeira cultura, usar apenas os percentuais do modelo e não falar de outras culturas; se não passar, fica o texto montado pelas regras.
8. **Gasto com a IA** (`services/openrouter.py`): cada pedido leva um preço máximo por token, aplicado pelo próprio OpenRouter, e há um orçamento por execução do servidor (`OPENROUTER_MAX_SPEND_USD`, padrão US$ 1). Ao atingi-lo, o sistema volta para as regras até reiniciar. As respostas ficam 24 h em cache. Medido: cerca de 15 s e US$ 0,001 por consulta nova. Como a rota não tem autenticação, defina também um limite na chave, no painel do OpenRouter. Sem `OPENROUTER_API_KEY`, tudo funciona só com as regras.

**Precisão do classificador** (2026-11-05): 51 notícias reais, rotuladas à mão antes de rodar. "Graves" são inversões entre positivo e negativo.

| Leitor | Rótulo exato | É da cultura? | Sentimento | Graves | Custo das 51 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Regras, na primeira medição | 67% | 86% | 74% | 1 | grátis |
| **inception/mercury-2.5** (padrão) | 76% | 92% | 79% | 0 | US$ 0,0038 |
| nvidia/nemotron-3.5-super-vl | 76% | 90% | 81% | 0 | US$ 0,0149 |
| mistralai/mistral-small-3.2 | 73% | 90% | 76% | 1 | US$ 0,0010 |
| openai/gpt-oss-20b | 73% | 90% | 77% | 1 | US$ 0,0029 |
| google/gemma-4-26b-a4b-it (reserva) | 71% | 84% | 80% | 0 | US$ 0,0007 |
| anthropic/claude-haiku-5.5 | 69% | 88% | 73% | 1 | US$ 0,0054 |
| google/gemini-2.5-flash-lite | 65% | 84% | 73% | 0 | US$ 0,0019 |
| deepseek/deepseek-v4-flash | 55% | 75% | 69% | 0 | US$ 0,0024 |

Leia com cautela. A amostra é pequena (cada notícia vale 2 pontos) e foi rotulada por uma só pessoa, sem revisão. As regras foram ajustadas depois dessa medição e chegaram a 78% na mesma amostra, número que já não é às cegas, e o prompt da IA também foi escrito depois de ver essas notícias. Em 8 notícias inéditas, regras, Mercury e Gemma empataram em 5 de 8. Não há evidência firme de que a IA classifique melhor que as regras: o ganho claro dela é a conclusão em texto corrido e não depender de um léxico mantido à mão. Trate o resultado como uma leitura rápida, por isso a tela sempre mostra as manchetes e um aviso.

Não há dados para provar que a ordem cruzada é melhor que a do modelo: notícia mostra que a cultura está em evidência, não que é boa para plantar. Soja e cana não fazem parte das 22 classes, então não aparecem no cruzamento.

**Limite conhecido:** as fontes só cobrem as notícias recentes. Culturas pouco presentes na imprensa brasileira (juta, feijão-moth, lentilha) e cidades pequenas muitas vezes não têm resultado. Nesses casos a tela informa isso, em vez de sugerir que a notícia é da região.

O KiPlanto exibe apenas título, resumo e imagem que o próprio veículo distribui, com crédito e link para a matéria. O corpo das matérias não é armazenado nem reproduzido. Detalhes em [docs/SPEC-noticias-colheita.md](docs/SPEC-noticias-colheita.md).

---

## Documentação

- [docs/RELATORIO-estado-atual.md](docs/RELATORIO-estado-atual.md): inventário de rotas, problemas encontrados e status das correções.
- [docs/SPEC-noticias-colheita.md](docs/SPEC-noticias-colheita.md): especificação das notícias regionais de colheita.
