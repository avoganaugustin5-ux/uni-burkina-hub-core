from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os
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
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════
# RECHERCHE
# ══════════════════════════════════════════════════════════

@app.get("/search", response_model=RechercheGlobaleResponse,
         summary="Recherche globale (documents + sujets forum)")
def search_global(
    q:      str = Query(..., min_length=2, description="Terme de recherche"),
    page:   int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=50)
):
    try:
        return recherche_globale(q, page=page, limite=limite)
    except Exception as e:
        raise HTTPException(503, f"Elasticsearch indisponible : {str(e)}")


@app.get("/search/documents", response_model=ResultatRecherche,
         summary="Rechercher dans les documents GED")
def search_documents(
    q:              str = Query(..., min_length=2),
    type_ressource: Optional[str] = None,
    id_filiere:     Optional[int] = None,
    page:           int = Query(1, ge=1),
    limite:         int = Query(10, ge=1, le=50)
):
    try:
        return rechercher_documents(q, type_ressource, id_filiere, page, limite)
    except Exception as e:
        raise HTTPException(503, f"Erreur recherche : {str(e)}")


@app.get("/search/sujets", response_model=ResultatRecherche,
         summary="Rechercher dans les sujets du forum")
def search_sujets(
    q:          str = Query(..., min_length=2),
    categorie:  Optional[str] = None,
    id_filiere: Optional[int] = None,
    page:       int = Query(1, ge=1),
    limite:     int = Query(10, ge=1, le=50)
):
    try:
        return rechercher_sujets(q, categorie, id_filiere, page, limite)
    except Exception as e:
        raise HTTPException(503, f"Erreur recherche : {str(e)}")


# ══════════════════════════════════════════════════════════
# INDEXATION
# ══════════════════════════════════════════════════════════

@app.post("/search/index/document", status_code=201,
          summary="Indexer un document GED dans Elasticsearch")
def index_document(data: IndexationDocument):
    try:
        indexer_document(data.model_dump())
        return {"message": f"Document {data.id_doc} indexe"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/search/index/sujet", status_code=201,
          summary="Indexer un sujet forum dans Elasticsearch")
def index_sujet(data: IndexationSujet):
    try:
        indexer_sujet(data.model_dump())
        return {"message": f"Sujet {data.id_sujet} indexe"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/search/index/document/{id_doc}",
            summary="Supprimer un document de l'index")
def delete_document(id_doc: int):
    supprimer_document(id_doc)
    return {"message": f"Document {id_doc} supprime de l'index"}


@app.delete("/search/index/sujet/{id_sujet}",
            summary="Supprimer un sujet de l'index")
def delete_sujet(id_sujet: int):
    supprimer_sujet(id_sujet)
    return {"message": f"Sujet {id_sujet} supprime de l'index"}


# ══════════════════════════════════════════════════════════
# REINDEXATION COMPLETE
# ══════════════════════════════════════════════════════════

@app.post("/search/reindex",
          summary="Reindexer tous les documents et sujets depuis les autres services")
async def reindex_tout():
    import httpx
    compte_docs = 0
    compte_sujets = 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                "http://localhost:8002/ged/documents",
                params={"statut": "VALIDE", "limite": 500}
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
                    })
                    compte_docs += 1

            r = await client.get(
                "http://localhost:8005/forum/sujets",
                params={"limite": 500}
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
def get_stats():
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