from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os, httpx
from dotenv import load_dotenv

load_dotenv()

from es_service import (
    init_elasticsearch, es,
    INDEX_DOCUMENTS, INDEX_SUJETS,
    indexer_document, indexer_sujet,
    supprimer_document, supprimer_sujet,
    rechercher_documents, rechercher_sujets,
    recherche_globale
)
from schemas import (
    ResultatRecherche, RechercheGlobaleResponse,
    IndexationDocument, IndexationSujet, SearchStats
)

API_AUTH = os.getenv("API_AUTH", "http://localhost:8001")
API_GED  = os.getenv("API_GED", "http://localhost:8002")
API_FORUM = os.getenv("API_FORUM", "http://localhost:8005")


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — authentification + périmètre (même pattern que service-ged)
# ══════════════════════════════════════════════════════════

async def verifier_token(authorization: Optional[str]) -> Optional[dict]:
    """Vérifie le JWT via service-auth et retourne le profil utilisateur."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{API_AUTH}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


async def get_perimetre(authorization: Optional[str]) -> dict:
    """Interroge service-auth pour le périmètre documentaire de l'utilisateur."""
    if not authorization:
        return {"poste_ids": [], "groupe_role_code": None, "vision_globale": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{API_AUTH}/auth/mon-perimetre",
                                  headers={"Authorization": authorization})
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"poste_ids": [], "groupe_role_code": None, "vision_globale": False}


async def exiger_utilisateur(authorization: Optional[str]) -> dict:
    """Exige une authentification valide ou lève 401."""
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    return user


async def exiger_admin(authorization: Optional[str]) -> dict:
    """Exige un utilisateur ADMIN/SOUS_ADMIN ou lève 403 (usage interne/admin)."""
    user = await exiger_utilisateur(authorization)
    if user.get("role") not in ("ADMIN", "SOUS_ADMIN"):
        raise HTTPException(403, "Réservé aux administrateurs.")
    return user


# ── Lifespan : init ES au démarrage sans bloquer ───────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_elasticsearch()
    yield

app = FastAPI(
    title="UniBurkina Hub — Service Search",
    description="Recherche full-text Elasticsearch sur documents GED et forum",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # "allow_origins=['*']" est incompatible avec credentials:include côté browser.
    # On liste les origines autorisées explicitement (frontend + accès direct local).
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,   # indispensable pour les cookies JWT HTTPOnly
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════
# RECHERCHE
# ══════════════════════════════════════════════════════════

@app.get("/search", response_model=RechercheGlobaleResponse,
         summary="Recherche globale (documents + sujets forum)")
async def search_global(
    q:      str = Query(..., min_length=2, description="Terme de recherche"),
    page:   int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=50),
    authorization: Optional[str] = Header(None),
):
    user = await exiger_utilisateur(authorization)
    is_admin = user.get("role") in ("ADMIN", "SOUS_ADMIN")
    postes_visibles = []
    if not is_admin:
        perimetre = await get_perimetre(authorization)
        postes_visibles = perimetre.get("poste_ids", [])
    try:
        return recherche_globale(q, page=page, limite=limite,
                                  postes_visibles=postes_visibles, is_admin=is_admin)
    except Exception as e:
        raise HTTPException(503, f"Elasticsearch indisponible : {str(e)}")


@app.get("/search/documents", response_model=ResultatRecherche,
         summary="Rechercher dans les documents GED")
async def search_documents(
    q:              str = Query(..., min_length=2),
    type_ressource: Optional[str] = None,
    id_filiere:     Optional[int] = None,
    page:           int = Query(1, ge=1),
    limite:         int = Query(10, ge=1, le=50),
    authorization:  Optional[str] = Header(None),
):
    user = await exiger_utilisateur(authorization)
    is_admin = user.get("role") in ("ADMIN", "SOUS_ADMIN")
    postes_visibles = []
    if not is_admin:
        perimetre = await get_perimetre(authorization)
        postes_visibles = perimetre.get("poste_ids", [])
    try:
        return rechercher_documents(q, type_ressource, id_filiere, page, limite,
                                     postes_visibles=postes_visibles, is_admin=is_admin)
    except Exception as e:
        raise HTTPException(503, f"Erreur recherche : {str(e)}")


@app.get("/search/sujets", response_model=ResultatRecherche,
         summary="Rechercher dans les sujets du forum")
async def search_sujets(
    q:          str = Query(..., min_length=2),
    categorie:  Optional[str] = None,
    id_filiere: Optional[int] = None,
    page:       int = Query(1, ge=1),
    limite:     int = Query(10, ge=1, le=50),
    authorization: Optional[str] = Header(None),
):
    await exiger_utilisateur(authorization)
    try:
        return rechercher_sujets(q, categorie, id_filiere, page, limite)
    except Exception as e:
        raise HTTPException(503, f"Erreur recherche : {str(e)}")


# ══════════════════════════════════════════════════════════
# INDEXATION
# ══════════════════════════════════════════════════════════

@app.post("/search/index/document", status_code=201,
          summary="Indexer un document GED dans Elasticsearch")
async def index_document(data: IndexationDocument, authorization: Optional[str] = Header(None)):
    await exiger_admin(authorization)
    try:
        indexer_document(data.model_dump())
        return {"message": f"Document {data.id_doc} indexe"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/search/index/sujet", status_code=201,
          summary="Indexer un sujet forum dans Elasticsearch")
async def index_sujet(data: IndexationSujet, authorization: Optional[str] = Header(None)):
    await exiger_admin(authorization)
    try:
        indexer_sujet(data.model_dump())
        return {"message": f"Sujet {data.id_sujet} indexe"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/search/index/document/{id_doc}",
            summary="Supprimer un document de l'index")
async def delete_document(id_doc: int, authorization: Optional[str] = Header(None)):
    await exiger_admin(authorization)
    supprimer_document(id_doc)
    return {"message": f"Document {id_doc} supprime de l'index"}


@app.delete("/search/index/sujet/{id_sujet}",
            summary="Supprimer un sujet de l'index")
async def delete_sujet(id_sujet: int, authorization: Optional[str] = Header(None)):
    await exiger_admin(authorization)
    supprimer_sujet(id_sujet)
    return {"message": f"Sujet {id_sujet} supprime de l'index"}


# ══════════════════════════════════════════════════════════
# REINDEXATION COMPLETE
# ══════════════════════════════════════════════════════════

@app.post("/search/reindex",
          summary="Reindexer tous les documents et sujets depuis les autres services")
async def reindex_tout(authorization: Optional[str] = Header(None)):
    import httpx
    await exiger_admin(authorization)
    compte_docs = 0
    compte_sujets = 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # AJOUT SECURITE UTS — l'Authorization est désormais transmise :
            # GET /ged/documents exige une authentification côté service-ged,
            # et le rôle admin garantit ici une vue non restreinte (tous les
            # documents, auteur_poste_id inclus pour le cloisonnement en recherche).
            r = await client.get(
                f"{API_GED}/ged/documents",
                params={"statut": "VALIDE", "limite": 500},
                headers={"Authorization": authorization},
            )
            if r.status_code == 200:
                for doc in r.json():
                    indexer_document({
                        "id_doc":          doc["id_doc"],
                        "titre":           doc["titre"],
                        "type_ressource":  doc["type_ressource"],
                        "texte_ocr":       doc.get("texte_ocr", ""),
                        "statut":          doc["statut"],
                        "id_filiere":      doc.get("id_filiere"),
                        "id_univ":         doc.get("id_univ"),
                        "date_soumission": doc.get("date_soumission"),
                        "auteur_poste_id": doc.get("auteur_poste_id"),
                    })
                    compte_docs += 1

            r = await client.get(
                f"{API_FORUM}/forum/sujets",
                params={"limite": 500},
                headers={"Authorization": authorization},
            )
            if r.status_code == 200:
                for sujet in r.json():
                    indexer_sujet({
                        "id_sujet":      sujet["id_sujet"],
                        "titre":         sujet["titre"],
                        "contenu":       sujet.get("contenu", ""),
                        "categorie":     sujet["categorie"],
                        "statut":        sujet["statut"],
                        "id_filiere":    sujet.get("id_filiere"),
                        "auteur_nom":    sujet.get("auteur_nom"),
                        "date_creation": sujet.get("date_creation"),
                    })
                    compte_sujets += 1

    except Exception as e:
        raise HTTPException(500, f"Erreur reindexation : {str(e)}")

    return {
        "message":           "Reindexation terminee",
        "documents_indexes": compte_docs,
        "sujets_indexes":    compte_sujets
    }


# ══════════════════════════════════════════════════════════
# STATISTIQUES
# ══════════════════════════════════════════════════════════

@app.get("/search/stats", response_model=SearchStats,
         summary="Statistiques des index Elasticsearch")
async def get_stats(authorization: Optional[str] = Header(None)):
    await exiger_utilisateur(authorization)
    try:
        nb_docs   = es.count(index=INDEX_DOCUMENTS)["count"]
        nb_sujets = es.count(index=INDEX_SUJETS)["count"]
        info      = es.info()
        return {
            "index_documents": nb_docs,
            "index_sujets":    nb_sujets,
            "es_status":       f"Elasticsearch {info['version']['number']} OK"
        }
    except Exception as e:
        raise HTTPException(503, str(e))


@app.get("/health", tags=["Systeme"])
def health():
    return {"status": "ok", "service": "uniburkina-search", "version": "1.0.0"}