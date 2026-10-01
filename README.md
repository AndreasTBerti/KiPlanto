# KiPlanto - Plataforma Agroclimática e Recomendação de Safra

Sistema inteligente de recomendação agronômica que integra modelo de Machine Learning (Random Forest) com telemetria meteorológica em tempo real (Open-Meteo) e análise de solo (N-P-K e pH).

---

## Estrutura do Projeto

```
KiPlanto/
├── main.py                  # Ponto de entrada FastAPI com middlewares CORS
├── requirements.txt         # Dependências do backend Python
├── .env.example             # Modelo de variáveis de ambiente
├── model/
│   ├── crop_model.py        # Pipeline de inferência e cálculo de probabilidades
│   └── modelo_recomendacao_safra.joblib # Modelo Random Forest treinado (22 culturas)
├── routers/
│   └── ai_router.py         # Rotas da API (/ai/prevision, /ai/prevision/direct, /ai/climate, /ai/crops)
├── schemas/
│   └── api_schema.py        # Schemas Pydantic tipados
├── services/
│   └── climate_data_service.py # Integração com APIs Open-Meteo e Geocoding
└── frontend/                # Interface moderna e enxuta (React + TypeScript + Tailwind CSS)
```

---

## Como Executar

### 1. Backend (FastAPI)

```bash
cd /home/victor/KiPlanto
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

### 2. Frontend (React + TypeScript + Vite)

```bash
cd /home/victor/KiPlanto/frontend
npm install
npm run dev
```

---

## Rotas da API

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/ai/prevision` | Recomendação automática por município e parâmetros de solo (N, P, K, pH) |
| `POST` | `/ai/prevision/direct` | Simulação direta com parâmetros edafoclimáticos manuais |
| `GET` | `/ai/climate/{city}` | Telemetria meteorológica e previsão de 7 dias via Open-Meteo |
| `GET` | `/ai/crops` | Lista das 22 culturas suportadas pelo modelo |
| `GET` | `/health` | Verificação de integridade |

---

## Módulos do Frontend

- **Recomendação de Safra**: Entrada de município com geocodificação automática, ajuste dos nutrientes do solo (Nitrogênio, Fósforo, Potássio e pH) e recomendação com probabilidades.
- **Simulação Direta**: Ajuste isolado das 6 variáveis edafoclimáticas com recálculo em tempo real.
- **Consulta Climática**: Consulta meteorológica detalhada de qualquer município.
- **Catálogo de Culturas**: Tabela taxonômica das 22 culturas suportadas pelo modelo com filtros por categoria.
- **Histórico de Análises**: Registro das simulações com detalhamento e exportação para JSON.
