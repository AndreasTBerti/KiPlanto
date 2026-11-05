# Relatório — Estado Atual do KiPlanto

| Campo | Valor |
| :--- | :--- |
| Data da verificação | 2026-11-03 |
| Commit analisado | `main` @ `fec9890` (merge do PR #1, frontend) |
| Status | **Os 17 problemas foram corrigidos no working tree, ainda sem commit** (ver §0) |
| Documento relacionado | [SPEC-noticias-colheita.md](SPEC-noticias-colheita.md) |

---

## 0. Status das correções (2026-11-03)

As seções 1 a 8 descrevem o sistema **como estava** em `fec9890` e foram mantidas como registro. Esta seção diz o que mudou.

| ID | Sev. | O que foi feito | Onde |
| :--- | :--- | :--- | :--- |
| P-01 | Alta | `rainfall` passou a ser a **chuva média mensal dos últimos 12 meses** (API de arquivo do Open-Meteo, ERA5). Tupã: de 2,01 para 126,7 mm/mês. Em 7 cidades testadas com o mesmo solo, antes todas davam muskmelon ~50%; agora o resultado acompanha o clima (jute nas mais chuvosas, papaya nas demais). | `services/climate_data_service.py`, `routers/ai_router.py` |
| P-02 | Alta | O pH virou **opcional** na API, com aviso na tela de que o modelo não o usa. A simulação parou de gravar pH 6,5 falso no histórico. Retreinar com pH ficou de fora porque o dataset de treino não está no repositório. | `schemas/api_schema.py`, `PredictionView`, `DirectSimulationView` |
| P-03 | Média | Temperatura **e umidade** (que tinha o mesmo problema) passaram a ser médias diárias dos próximos 7 dias, em vez da leitura do momento. | `services/climate_data_service.py` |
| P-04 | Alta | `venv/` corrigido pela sessão paralela que implementa a SPEC: `pip uninstall dotenv` + `pip install -r requirements-dev.txt`. O modelo carrega sem `InconsistentVersionWarning`. | `venv/` (local) |
| P-05 | Média | `scikit-learn==1.6.1`; `numpy>=2,<3`, porque o pickle referencia `numpy._core` e não carrega com numpy 1.x; teto de versão major nas demais dependências. | `requirements.txt` |
| P-06 | Média | Limites físicos (`ge`/`le`) em todos os campos numéricos, `allow_inf_nan=False`, cidade com 2–80 caracteres, UF validada. Fora disso: 422. | `schemas/api_schema.py` |
| P-07 | Média | Origens vêm de `CORS_ALLOW_ORIGINS` (padrão: localhost 3000/4173), sem credenciais, só GET/POST. Preflight de origem desconhecida: 400, sem `allow-origin`. | `main.py` |
| P-08 | Média | 404 para cidade não encontrada e 502 para falha do Open-Meteo. Retry com backoff em 429/5xx. Cache em memória (geocodificação 24 h, previsão 15 min, chuva 24 h). Previsão e histórico em paralelo. Medido: ~0,5 s por cidade nova (2,9 s na primeira chamada do processo) e ~40 ms em consulta repetida. | `services/climate_data_service.py`, `routers/ai_router.py` |
| P-09 | Baixa | URL da API via `VITE_API_URL`; vazio = mesma origem + proxy do Vite. Removidos `setApiBaseUrl` e o override por `localStorage`. Criado `frontend/.env.example`. | `frontend/src/services/api.ts` |
| P-10 | Baixa | O catálogo é conferido com `GET /ai/crops` e mostra divergências entre o dicionário e o modelo. | `CropsCatalogView.tsx` |
| P-11 | Baixa | `get_coordinates(..., state=)` com `state`/`uf` na resposta; UF opcional nas telas de Recomendação e Clima. Com UF, só aceita nome exato: antes, "Tupã" + RS devolvia "Tuparendi". | `services/climate_data_service.py`, `services/br_states.py`, views |
| P-12 | Baixa | Nomes corrigidos (`crop_recommendation`, `temperature_mean_7d`, `precipitation_total_7d` etc.). Os antigos continuam como **obsoletos**. O histórico salvo no navegador é migrado ao carregar. Handlers renomeados para `get_prevision` e `get_direct_prevision`. | `schemas/`, `routers/ai_router.py`, frontend |
| P-13 | Baixa | 63 testes para as rotas `/ai/*` e o serviço de clima (144 no total, com os de notícias), `ruff` configurado e CI no GitHub Actions. | `tests/`, `ruff.toml`, `.github/workflows/ci.yml` |
| P-14 | Baixa | `npm run lint`: 0 warnings e 0 erros. | `ClimateView.tsx`, `DirectSimulationView.tsx` |
| P-15 | Baixa | Removidos 6 arquivos do template (`App.css`, `src/assets/*`, `public/*`) e a interface `CropInfo`. | `frontend/` |
| P-16 | Baixa | README reescrito: setup no Windows e no Linux, rotas com códigos de erro, variáveis de ambiente, testes e campos obsoletos. | `README.md` |
| P-17 | Baixa | Removidos o default `"tupã"` e os valores-padrão escondidos de `crop_prev` (25 °C / 70 % / 100 mm). O pH ficou sem default. Confiança 0% agora aparece. | `climate_data_service.py`, `crop_model.py`, views |

**Verificação final:** `pytest` com 144 testes passando, `ruff check .` limpo, `npm run build` e `npm run lint` limpos, e teste de ponta a ponta contra o Open-Meteo real.

**Rotas hoje:** 7 de aplicação (as 6 originais + `GET /news`, da feature de notícias) + 4 automáticas do FastAPI = **11**.

**Observações:**
- **Escolha de modelagem (P-01):** "chuva média mensal dos últimos 12 meses" é a interpretação que encaixa na faixa do modelo (30–265 mm). É uma decisão de projeto, não um fato verificado no dataset de treino, que não está no repositório. A janela fica em `RAINFALL_HISTORY_DAYS` (`services/climate_data_service.py`).
- **Limite do próprio modelo:** com as escalas corretas a recomendação passou a responder ao clima, mas as 22 classes vêm de um dataset indiano. Culturas como jute e mothbeans representam pouco a agricultura brasileira. Isso não se resolve no pipeline; só com outro dataset.

---

## Resumo (estado em `fec9890`, antes das correções)

| Item | Situação |
| :--- | :--- |
| **Rotas HTTP do backend** | **10** no total: **6 de aplicação** (`/`, `/health` e 4 em `/ai/*`) + **4 geradas pelo FastAPI** (`/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect`) |
| **Rotas usadas pelo frontend** | **3 de 6**: `/ai/prevision`, `/ai/prevision/direct`, `/ai/climate/{city}` |
| **Telas do frontend** | **5**, navegadas por estado (`activeTab`), sem roteador de URL |
| Backend em ambiente limpo | Sobe e responde 200 em todas as rotas (teste completo na §4) |
| Backend no `venv/` local | **Não sobe**: `ModuleNotFoundError: No module named 'joblib'` |
| Frontend | `npm run build` OK (270 KB JS, 80 KB gzip); `npm run lint`: 0 erros, 2 warnings |
| Testes / CI | Nenhum teste automatizado, sem CI |
| **Problemas encontrados** | 17 no total (§6): **2 graves no pipeline de recomendação** (P-01 chuva fora de escala, P-02 pH ignorado), **1 de ambiente** que impede rodar o backend (P-04) e 14 de severidade média ou baixa |

## 1. Como a verificação foi feita

Nada no repositório foi alterado.

1. Leitura de todo o código rastreado (41 arquivos; 314 linhas de Python em 5 módulos, 1.636 linhas de TS/TSX em 11 arquivos).
2. **Backend:** o `venv/` do projeto não tem as dependências. Criei um venv **isolado** (fora do repositório) com `pip install -r requirements.txt`, subi `uvicorn main:app` e rodei um smoke test em todas as rotas, com casos de erro e de borda.
3. **Modelo:** carregado e inspecionado (tipo, classes, features, importâncias, limiares das árvores, versão do scikit-learn usada no treino).
4. **Frontend:** cópia de `frontend/` fora do repositório, `npm ci`, `npm run build` e `npm run lint`.
5. **APIs externas:** chamadas reais à geocodificação e à previsão do Open-Meteo.

## 2. Arquitetura atual

```
┌────────────────────── Frontend (React 19 + Vite 8 + Tailwind 4) ──────────────────────┐
│ App.tsx ── activeTab ──► PredictionView │ DirectSimulationView │ ClimateView │        │
│                          CropsCatalogView (estático) │ HistoryView (localStorage)      │
│ services/api.ts ──fetch──► http://localhost:8000 (URL absoluta; proxy do Vite não usado)│
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           ▼
┌──────────────────────────── Backend (FastAPI, main.py) ───────────────────────────────┐
│ GET /, GET /health                                                                    │
│ routers/ai_router.py  (prefix /ai)                                                    │
│   ├─ POST /prevision ──► services/climate_data_service ──► Open-Meteo (geo + forecast)│
│   │                  └─► model/crop_model.crop_prev ──► RandomForest (.joblib)        │
│   ├─ POST /prevision/direct ──► crop_prev                                             │
│   ├─ GET  /climate/{city} ──► climate_data_service                                    │
│   └─ GET  /crops ──► model.classes_                                                   │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

Não há banco de dados nem autenticação. O único estado persistente é o histórico de análises, guardado no `localStorage` do navegador (chave `kiplanto_history`, máximo de 50 itens).

## 3. Inventário de rotas

### 3.1 Backend: 6 rotas de aplicação

Os tempos medidos incluem a latência real das APIs externas.

| # | Método | Rota | Handler | Entrada | Dependências | Usada pelo front? | Teste |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | GET | `/` | `home` ([main.py:21](../main.py#L21)) | — | — | Não | 200, 12 ms |
| 2 | GET | `/health` | `health` ([main.py:37](../main.py#L37)) | — | — | **Não** (`checkApiHealth` existe em `api.ts`, mas nenhuma tela chama) | 200, 17 ms |
| 3 | POST | `/ai/prevision` | `get_prev` ([ai_router.py:8](../routers/ai_router.py#L8)) | `city`, `n_ratio`, `p_ratio`, `k_ratio`, `ph` | Open-Meteo geo + forecast, modelo | Sim, `PredictionView` | 200, **3,5 s** |
| 4 | POST | `/ai/prevision/direct` | `get_direct_prev` ([ai_router.py:39](../routers/ai_router.py#L39)) | `n`, `p`, `k`, `temperature`, `humidity`, `rainfall`, `ph?` | modelo | Sim, `DirectSimulationView` | 200, ~70 ms |
| 5 | GET | `/ai/climate/{city}` | `get_city_climate` ([ai_router.py:63](../routers/ai_router.py#L63)) | `city` (path) | Open-Meteo geo + forecast | Sim, `ClimateView` | 200, **3,1 s**; cidade inexistente → 400, 1,9 s |
| 6 | GET | `/ai/crops` | `list_supported_crops` ([ai_router.py:79](../routers/ai_router.py#L79)) | — | modelo | **Não** (`getSupportedCrops` existe, mas o catálogo usa dicionário estático) | 200, **3,4 s** na 1ª chamada (carga do modelo), 9 ms depois |

### 3.2 Backend: 4 rotas automáticas do FastAPI

| Rota | Função | Teste |
| :--- | :--- | :--- |
| `GET /docs` | Swagger UI | 200 |
| `GET /redoc` | ReDoc | 200 |
| `GET /openapi.json` | Esquema OpenAPI | 200 |
| `GET /docs/oauth2-redirect` | Auxiliar do Swagger | 200 |

### 3.3 A documentação diverge do código

| Local | Rotas listadas | Diferença |
| :--- | :--- | :--- |
| Endpoint `GET /` ([main.py:27-34](../main.py#L27-L34)) | 6 | Correto |
| `README.md`, seção "Rotas da API" | 5 | Falta `GET /` |
| Nenhum dos dois | — | Não mencionam `/docs` e `/redoc`, úteis para quem for testar |

### 3.4 Frontend: telas (sem roteador de URL)

A navegação é um `useState<NavTab>` em [App.tsx:13](../frontend/src/App.tsx#L13). Não há URL por tela: recarregar a página sempre volta para "Recomendação de Safra" e não existe link direto para uma tela.

| # | `NavTab` | Rótulo | Componente | Fonte de dados | Grava no histórico? |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `prediction` | Recomendação de Safra | `PredictionView` | `POST /ai/prevision` | Sim |
| 2 | `simulation` | Simulação Direta | `DirectSimulationView` | `POST /ai/prevision/direct` (automático, debounce de 250 ms) | Só com o auto-simular desligado |
| 3 | `climate` | Consulta Climática | `ClimateView` | `GET /ai/climate/{city}` | Não |
| 4 | `catalog` | Catálogo de Culturas | `CropsCatalogView` | `CROP_DICTIONARY` **estático** ([types/api.ts:81](../frontend/src/types/api.ts#L81)) | Não |
| 5 | `history` | Histórico de Análises | `HistoryView` | `localStorage` | (lê e exporta JSON) |

### 3.5 Frontend: funções de `services/api.ts`

| Função | Usada em | Situação |
| :--- | :--- | :--- |
| `predictCrop` | PredictionView | Em uso |
| `predictCropDirect` | DirectSimulationView | Em uso |
| `getCityClimate` | ClimateView | Em uso |
| `getApiBaseUrl` | uso interno | Em uso |
| `checkApiHealth` | — | **Sem uso** |
| `getSupportedCrops` | — | **Sem uso** |
| `setApiBaseUrl` | — | **Sem uso**: a URL da API só muda editando o `localStorage` no DevTools |

## 4. Resultado dos testes de execução

### 4.1 Smoke test (ambiente limpo, `requirements.txt` atual)

```
[200]    12 ms  GET /
[200]    17 ms  GET /health
[200]  3399 ms  GET /ai/crops            (1ª chamada: carrega o modelo)
[200]     9 ms  GET /ai/crops            (2ª chamada)
[200]  3079 ms  GET /ai/climate/Tupã
[400]  1939 ms  GET /ai/climate/CidadeQueNaoExisteXyz
[200]  3500 ms  POST /ai/prevision  {city: Tupã, N60 P45 K50 pH6.5}  → muskmelon 51%
[422]     9 ms  POST /ai/prevision  sem "ph"
[200]    74 ms  POST /ai/prevision/direct  n = -500        → aceito, "mango"
[200]    69 ms  POST /ai/prevision/direct  humidity = 500  → aceito, "papaya"
[200]  GET /docs · /redoc · /openapi.json · /docs/oauth2-redirect
```

### 4.2 Ambiente local do repositório (`venv/`)

```
$ python -c "from main import app"
ModuleNotFoundError: No module named 'joblib'
```

O `venv/` tem só `fastapi`, `uvicorn`, `pydantic`, `requests` e `python-dotenv`. Faltam `joblib`, `scikit-learn`, `pandas` e `numpy`. Ele também tem o pacote **`dotenv 0.9.9`**, que é outro pacote, diferente de `python-dotenv`, e não deveria estar instalado.

### 4.3 Frontend

```
npm ci            → 45 pacotes
npm run build     → OK · dist/assets/index.js 270,30 kB (gzip 80,09 kB) · CSS 30,13 kB
npm run lint      → 0 erros, 2 warnings:
  ClimateView.tsx:41          react(set-state-in-effect)
  DirectSimulationView.tsx:66 react-hooks(exhaustive-deps): falta 'runSimulation'
```

## 5. Modelo de Machine Learning

| Atributo | Valor |
| :--- | :--- |
| Arquivo | `model/modelo_recomendacao_safra.joblib`, 3,37 MB, versionado no git |
| Tipo | `sklearn.ensemble.RandomForestClassifier`, 100 árvores, `max_depth=None` |
| Classes | 22: apple, banana, blackgram, chickpea, coconut, coffee, cotton, grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, rice, watermelon |
| Features | 6, nesta ordem: `N`, `P`, `K`, `temperature`, `humidity`, `rainfall`. **Não inclui `ph`.** |
| Versão do treino | scikit-learn **1.6.1** |
| Versão instalada hoje por `requirements.txt` | scikit-learn **1.9.1** (pin é só `>=1.4.0`) → **102 `InconsistentVersionWarning`** ao carregar |
| Carregamento | Lazy, no primeiro request (+~3,4 s nessa chamada) |

Faixas que o modelo "conhece", extraídas dos limiares de corte das 100 árvores. Valores fora da faixa caem sempre no mesmo ramo da extremidade:

| Feature | Menor corte | Maior corte | Importância |
| :--- | ---: | ---: | ---: |
| N | 0,50 | 126,00 | 0,110 |
| P | 7,00 | 144,50 | 0,159 |
| K | 14,50 | 202,50 | 0,185 |
| temperature | 16,21 | 37,05 | 0,068 |
| humidity | 17,87 | 95,95 | 0,227 |
| **rainfall** | **30,02** | 265,33 | **0,252** (a mais importante) |

## 6. Problemas encontrados

Severidade: **Alta** = resultado errado ou sistema não roda; **Média** = risco real, mas contornável; **Baixa** = qualidade e manutenção.

### P-01 · Alta · A chuva enviada ao modelo está fora de escala em `/ai/prevision`

- **Onde:** [ai_router.py:25](../routers/ai_router.py#L25) usa `preciptation_forecast`, calculado em [climate_data_service.py:74](../services/climate_data_service.py#L74) como `sum(precipitation_sum) / len(...)`. Apesar do nome `..._sum`, isso é a **média diária** dos 7 dias de previsão.
- **Evidência:** para Tupã o valor enviado foi **2,01 mm**. O menor corte de `rainfall` em todo o modelo é **30,02 mm**, então qualquer valor abaixo de 30 é tratado igual. Teste direto, com as demais variáveis fixas:

  | rainfall | 0 | 2 | 5 | 50 | 100 | 200 |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
  | Resultado | muskmelon 48% | muskmelon 48% | muskmelon 48% | papaya 22% | maize 26% | jute 43% |

- **Impacto:** a feature mais importante do modelo (25%) fica presa no extremo "seco" em praticamente toda recomendação por cidade. O resultado tende a culturas de clima seco, seja qual for o clima real.
- **Recomendação:** conferir com quem treinou o modelo qual agregação de chuva o dataset usa. A faixa de 30–265 mm é compatível com acumulado mensal ou sazonal, não com média diária. Depois disso, alimentar um valor equivalente, por exemplo o acumulado histórico do mês pela API de arquivo do Open-Meteo, e renomear a variável.

### P-02 · Alta · O pH é coletado, mas o modelo ignora

- **Onde:** `ph` é **obrigatório** em `PrevisionInput` ([api_schema.py:9](../schemas/api_schema.py#L9); omitir dá 422), tem slider na tela ([PredictionView.tsx:188-203](../frontend/src/components/views/PredictionView.tsx#L188-L203)) e vai para o histórico. Mas o modelo não tem essa feature e `crop_prev` nem lê o campo.
- **Evidência:** mesma entrada com pH 3,5 e pH 9,0 → `coffee 70%` nos dois casos.
- **Impacto:** a interface sugere que o pH influencia a recomendação, e isso não é verdade.
- **Recomendação:** ou retreinar incluindo `ph` (o dataset de 22 culturas normalmente tem essa coluna), ou tornar o campo opcional e mostrar "não utilizado pelo modelo atual".

### P-03 · Média · Temperatura instantânea no lugar da média

- **Onde:** [ai_router.py:23](../routers/ai_router.py#L23) usa `temperature`, a leitura do momento. No teste: 30,1 °C às 14h, enquanto a média prevista de 7 dias era 24,47 °C.
- **Impacto:** a recomendação muda conforme a hora do dia em que a consulta é feita.
- **Recomendação:** usar `temperature_forecast` (média) ou uma média histórica, alinhada com o que foi usado no treino.

### P-04 · Alta (ambiente) · O `venv/` local não roda o backend

- **Evidência:** §4.2.
- **Correção:** `venv\Scripts\python -m pip uninstall -y dotenv`, depois `venv\Scripts\python -m pip install -r requirements.txt`.

### P-05 · Média · Versões sem pin e modelo treinado em outra versão do scikit-learn

- **Evidência:** §5. Treinado na 1.6.1, instala a 1.9.1, 102 avisos de incompatibilidade. Hoje funciona, mas uma versão futura pode quebrar o unpickle ou mudar resultados sem avisar.
- **Recomendação:** fixar `scikit-learn==1.6.1` com `numpy`/`pandas` compatíveis, ou re-exportar o modelo na versão atual e fixar essa. Vale também fixar as demais dependências.

### P-06 · Média · Sem validação de faixa nas entradas

- **Evidência:** `n=-500` e `humidity=500` aceitos com 200 e uma recomendação.
- **Recomendação:** `Field(ge=..., le=...)` nos schemas (ex.: `humidity` 0–100, nutrientes ≥ 0), com limites coerentes com a §5.

### P-07 · Média (segurança) · CORS aceita qualquer origem com credenciais

- **Onde:** [main.py:11-17](../main.py#L11-L17), `allow_origins=["*"]` com `allow_credentials=True`.
- **Evidência:** preflight vindo de `Origin: https://evil.example` → `access-control-allow-origin: https://evil.example` e `access-control-allow-credentials: true`.
- **Impacto atual:** baixo, porque não há autenticação nem cookies. Mas o padrão é perigoso se isso mudar.
- **Recomendação:** origens permitidas via `.env` (ex.: `http://localhost:3000`) e `allow_credentials=False` enquanto não houver sessão.

### P-08 · Média · Erros externos viram 400 e chamadas são sequenciais

- **Onde:** [ai_router.py:13-17](../routers/ai_router.py#L13-L17) e [:73-77](../routers/ai_router.py#L73-L77) capturam `Exception` e devolvem **400**, inclusive quando o Open-Meteo cai, o que deveria ser 502/503. Não há retry nem cache, e geocodificação + previsão rodam em sequência (cerca de 2–3,5 s por request).
- **Recomendação:** separar "cidade não encontrada" (400/404) de "falha do provedor" (502); cachear a geocodificação por cidade.

### P-09 · Baixa · Configuração de URL da API inconsistente no frontend

- `DEFAULT_API_URL = 'http://localhost:8000'` ([api.ts:3](../frontend/src/services/api.ts#L3)) é absoluto, então o proxy de `vite.config.ts` (`/ai`, `/health`) **nunca é usado**.
- `setApiBaseUrl` não tem tela, o que dificulta apontar o front para outro servidor.
- **Recomendação:** usar `import.meta.env.VITE_API_URL` com fallback `''` (relativo, aproveitando o proxy).

### P-10 · Baixa · Catálogo estático duplica as classes do modelo

- `CropsCatalogView` lê `CROP_DICTIONARY` fixo no código e `/ai/crops` não é chamado. Se o modelo for retreinado com outras culturas, o catálogo fica desatualizado sem ninguém perceber.
- **Recomendação:** cruzar `/ai/crops` com o dicionário e sinalizar classes sem tradução.

### P-11 · Baixa · Geocodificação ambígua e o estado é descartado

- [climate_data_service.py:27](../services/climate_data_service.py#L27) pega o 1º resultado sem filtro de estado e descarta `admin1`. Teste: "Tupã" existe em SP e no PA; "São José" retorna Santa Catarina primeiro.
- A SPEC de notícias resolve isso (§5.2 da SPEC), o que também beneficia clima e recomendação.

### P-12 · Baixa · Erros de grafia no contrato público

- `crop_recomendation`, `preciptation_forecast`, `get_prev`. Corrigir quebra o frontend; se for feito, expor os dois nomes durante a transição (alias Pydantic).

### P-13 · Baixa · Sem testes automatizados, sem CI, sem lint de Python

- Recomendação mínima: `pytest` com `TestClient` para as 6 rotas, mockando o Open-Meteo, e um workflow no GitHub Actions rodando `pytest` + `npm run build` + `npm run lint`.

### P-14 · Baixa · Warnings de lint no frontend

- `ClimateView.tsx:41` (setState dentro de effect) e `DirectSimulationView.tsx:66` (dependência faltando no `useEffect`).

### P-15 · Baixa · Arquivos do template Vite sem uso

- `src/App.css`, `src/assets/hero.png`, `src/assets/react.svg`, `src/assets/vite.svg`, `public/favicon.svg` e `public/icons.svg` não são referenciados. O `index.html` também não declara favicon. A interface `CropInfo` ([types/api.ts:68](../frontend/src/types/api.ts#L68)) não é usada.

### P-16 · Baixa · README desatualizado para o time

- Caminhos fixos de uma máquina específica (`/home/victor/KiPlanto`) e só o comando de ativação do Linux (`source venv/bin/activate`). No Windows é `venv\Scripts\activate`.
- Tabela de rotas sem `GET /` (§3.3).

### P-17 · Baixa · Detalhes de código

- `get_coordinates(city="tupã")` tem default escondido ([climate_data_service.py:10](../services/climate_data_service.py#L10)); melhor deixar obrigatório.
- `DirectPrevisionInput.ph` existe com default 6.5, mas também não é usado.
- `PredictionView` mostra o selo de confiança com `result.confidence && ...`, que esconde o valor 0.

## 7. Recomendações em ordem

| Ordem | Ação | Problemas | Esforço |
| :-: | :--- | :--- | :--- |
| 1 | Consertar o `venv/` local | P-04 | minutos |
| 2 | Fixar a versão do scikit-learn (e demais deps) | P-05 | minutos |
| 3 | Decidir com quem treinou o modelo: agregação de chuva, temperatura e pH | P-01, P-02, P-03 | reunião + ajuste em 2 arquivos |
| 4 | Validação de faixa nos schemas + CORS por `.env` | P-06, P-07 | < 1 h |
| 5 | Testes mínimos das 6 rotas + CI | P-13 | meio período |
| 6 | Implementar a feature de notícias (já corrige P-11) | — | ver SPEC §10 |
| 7 | Limpeza: lint, arquivos órfãos, README, URL da API | P-09, P-10, P-14–P-17 | < 1 h |

Os itens 1 e 2 são pré-requisito para qualquer pessoa do time rodar o backend. Os itens 3 a 5 tratam do que hoje dá resultado errado sem dar erro.

## 8. Rotas após a feature de notícias

| | Hoje | MVP de notícias | Com a P1 |
| :--- | :-: | :-: | :-: |
| Rotas de aplicação | 6 | **7** (+`GET /news`) | **8** (+`GET /news/{article_id}`) |
| Rotas automáticas (FastAPI) | 4 | 4 | 4 |
| **Total HTTP** | **10** | **11** | **12** |
| Telas do frontend | 5 | **6** (+Notícias da Colheita) | 6 (+card na Recomendação) |
