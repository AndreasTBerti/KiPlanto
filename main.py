from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.ai_router import router as ai_router

app = FastAPI(
    title="KiPlanto API",
    description="API de recomendação inteligente de safras e dados agroclimáticos",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "KiPlanto API",
        "version": "1.0.0",
        "endpoints": [
            {"method": "GET", "path": "/", "description": "Status da API"},
            {"method": "GET", "path": "/health", "description": "Healthcheck do serviço"},
            {"method": "POST", "path": "/ai/prevision", "description": "Recomendação de safra por cidade e solo"},
            {"method": "POST", "path": "/ai/prevision/direct", "description": "Simulação direta de safra"},
            {"method": "GET", "path": "/ai/climate/{city}", "description": "Consulta meteorológica por cidade"},
            {"method": "GET", "path": "/ai/crops", "description": "Culturas suportadas pelo modelo"}
        ]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "uptime": "ok"}