import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.ai_router import router as ai_router
from routers.auth_router import require_user
from routers.auth_router import router as auth_router
from routers.news_router import router as news_router

load_dotenv()

app = FastAPI(
    title="KiPlanto API",
    description="API de recomendação inteligente de safras e dados agroclimáticos",
    version="1.0.0"
)

# Origens liberadas no CORS, separadas por vírgula. No `npm run dev` o front chama
# a API pelo proxy do Vite (mesma origem), então o CORS só importa quando o front
# aponta para outra origem via VITE_API_URL. A sessão vai no cabeçalho Authorization,
# não em cookie: sem credenciais.
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173"
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in (os.getenv("CORS_ALLOW_ORIGINS") or DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.include_router(auth_router)
# Só com login: estas rotas consultam serviços externos, e a recomendação cruzada gasta créditos de IA.
app.include_router(ai_router, dependencies=[Depends(require_user)])
app.include_router(news_router, dependencies=[Depends(require_user)])

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "KiPlanto API",
        "version": "1.0.0",
        "endpoints": [
            {"method": "GET", "path": "/", "description": "Status da API"},
            {"method": "GET", "path": "/health", "description": "Healthcheck do serviço"},
            {"method": "POST", "path": "/auth/register", "description": "Cria uma conta e inicia a sessão"},
            {"method": "POST", "path": "/auth/login", "description": "Inicia uma sessão"},
            {"method": "POST", "path": "/auth/logout", "description": "Encerra a sessão atual"},
            {"method": "GET", "path": "/auth/me", "description": "A conta da sessão atual"},
            {"method": "POST", "path": "/ai/prevision", "description": "Recomendação de safra por cidade e solo"},
            {"method": "POST", "path": "/ai/prevision/direct", "description": "Simulação direta de safra"},
            {
                "method": "POST",
                "path": "/ai/cross-recommendation",
                "description": "Cruza a recomendação do modelo com as notícias da região",
            },
            {"method": "GET", "path": "/ai/climate/{city}", "description": "Consulta meteorológica por cidade"},
            {"method": "GET", "path": "/ai/crops", "description": "Culturas suportadas pelo modelo"},
            {
                "method": "GET",
                "path": "/news",
                "description": "Notícias de colheita por cidade/UF (crop busca a cultura indicada)",
            },
        ]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "uptime": "ok"}
