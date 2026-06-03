from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import Base
from routes import router

# Crée toutes les tables au démarrage
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UniBurkina Hub — Service Authentification",
    description="Gestion des utilisateurs, rôles, JWT et arborescence académique",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — autorise le frontend à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/auth", tags=["Authentification & Utilisateurs"])

@app.get("/health", tags=["Système"])
def health():
    return {
        "status": "ok",
        "service": "uniburkina-auth",
        "version": "1.0.0"
    }