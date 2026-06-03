from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from database import engine, get_db
from models import Base, Sujet, Reponse, Signalement, StatutPostEnum, CategorieEnum
from schemas import (
    SujetCreate, SujetResponse, SujetResume,
    ReponseCreate, ReponseResponse,
    ModerationAction, SignalementCreate, SignalementResponse,
    ForumStats
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UniBurkina Hub — Service Forum",
    description="Forum et FAQ par filiere avec moderation (UC_02)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════
# SUJETS
# ══════════════════════════════════════════════════════════

@app.post("/forum/sujets", response_model=SujetResponse,
          status_code=201, summary="Creer un nouveau sujet")
def creer_sujet(data: SujetCreate, db: Session = Depends(get_db)):
    sujet = Sujet(**data.model_dump())
    db.add(sujet)
    db.commit()
    db.refresh(sujet)
    return sujet


@app.get("/forum/sujets", response_model=List[SujetResume],
         summary="Liste des sujets (avec filtres et pagination)")
def list_sujets(
    categorie:  Optional[str] = None,
    id_filiere: Optional[int] = None,
    id_univ:    Optional[int] = None,
    recherche:  Optional[str] = None,
    epingles_d_abord: bool    = True,
    page:       int = Query(1, ge=1),
    limite:     int = Query(20, ge=1, le=100),
    db:         Session = Depends(get_db)
):
    query = db.query(Sujet).filter(Sujet.statut == StatutPostEnum.VISIBLE)

    if categorie:
        query = query.filter(Sujet.categorie == categorie)
    if id_filiere:
        query = query.filter(Sujet.id_filiere == id_filiere)
    if id_univ:
        query = query.filter(Sujet.id_univ == id_univ)
    if recherche:
        query = query.filter(Sujet.titre.ilike(f"%{recherche}%"))

    if epingles_d_abord:
        query = query.order_by(Sujet.est_epingle.desc(),
                               Sujet.date_creation.desc())
    else:
        query = query.order_by(Sujet.date_creation.desc())

    sujets = query.offset((page - 1) * limite).limit(limite).all()

    # Ajouter nb_reponses à chaque sujet
    result = []
    for s in sujets:
        nb = db.query(func.count(Reponse.id_reponse)).filter(
            Reponse.id_sujet == s.id_sujet,
            Reponse.statut == StatutPostEnum.VISIBLE
        ).scalar()
        item = SujetResume(
            id_sujet=s.id_sujet, titre=s.titre,
            categorie=s.categorie, statut=s.statut,
            est_epingle=s.est_epingle, est_resolu=s.est_resolu,
            nb_vues=s.nb_vues, nb_reponses=nb,
            date_creation=s.date_creation, auteur_nom=s.auteur_nom,
            id_filiere=s.id_filiere
        )
        result.append(item)
    return result


@app.get("/forum/sujets/{id_sujet}", response_model=SujetResponse,
         summary="Detail d'un sujet + toutes ses reponses")
def get_sujet(id_sujet: int, db: Session = Depends(get_db)):
    sujet = db.get(Sujet, id_sujet)
    if not sujet:
        raise HTTPException(404, "Sujet introuvable")
    if sujet.statut == StatutPostEnum.MASQUE:
        raise HTTPException(403, "Ce sujet a ete masque par un moderateur")

    # Incrémenter le compteur de vues
    sujet.nb_vues += 1
    db.commit()
    db.refresh(sujet)
    return sujet


@app.delete("/forum/sujets/{id_sujet}",
            summary="Supprimer un sujet (auteur ou moderateur)")
def supprimer_sujet(id_sujet: int, db: Session = Depends(get_db)):
    sujet = db.get(Sujet, id_sujet)
    if not sujet:
        raise HTTPException(404, "Sujet introuvable")
    db.delete(sujet)
    db.commit()
    return {"message": f"Sujet '{sujet.titre}' supprime"}


# ══════════════════════════════════════════════════════════
# REPONSES
# ══════════════════════════════════════════════════════════

@app.post("/forum/sujets/{id_sujet}/reponses",
          response_model=ReponseResponse,
          status_code=201, summary="Repondre a un sujet")
def creer_reponse(
    id_sujet: int,
    data:     ReponseCreate,
    db:       Session = Depends(get_db)
):
    sujet = db.get(Sujet, id_sujet)
    if not sujet:
        raise HTTPException(404, "Sujet introuvable")
    if sujet.statut == StatutPostEnum.MASQUE:
        raise HTTPException(403, "Impossible de repondre a un sujet masque")

    reponse = Reponse(id_sujet=id_sujet, **data.model_dump())
    db.add(reponse)
    db.commit()
    db.refresh(reponse)
    return reponse


@app.post("/forum/reponses/{id_reponse}/like",
          summary="Liker une reponse")
def liker_reponse(id_reponse: int, db: Session = Depends(get_db)):
    reponse = db.get(Reponse, id_reponse)
    if not reponse:
        raise HTTPException(404, "Reponse introuvable")
    reponse.nb_likes += 1
    db.commit()
    return {"nb_likes": reponse.nb_likes}


@app.put("/forum/reponses/{id_reponse}/solution",
         summary="Marquer une reponse comme solution acceptee")
def marquer_solution(id_reponse: int, db: Session = Depends(get_db)):
    reponse = db.get(Reponse, id_reponse)
    if not reponse:
        raise HTTPException(404, "Reponse introuvable")

    # Retirer l'ancienne solution si elle existe
    db.query(Reponse).filter(
        Reponse.id_sujet == reponse.id_sujet,
        Reponse.est_solution == True
    ).update({"est_solution": False})

    reponse.est_solution = True

    # Marquer le sujet comme résolu
    sujet = db.get(Sujet, reponse.id_sujet)
    if sujet:
        sujet.est_resolu = True

    db.commit()
    return {"message": "Reponse marquee comme solution", "id_reponse": id_reponse}


@app.delete("/forum/reponses/{id_reponse}",
            summary="Supprimer une reponse")
def supprimer_reponse(id_reponse: int, db: Session = Depends(get_db)):
    reponse = db.get(Reponse, id_reponse)
    if not reponse:
        raise HTTPException(404, "Reponse introuvable")
    db.delete(reponse)
    db.commit()
    return {"message": "Reponse supprimee"}


# ══════════════════════════════════════════════════════════
# MODERATION (SOUS_ADMIN)
# ══════════════════════════════════════════════════════════

@app.put("/forum/moderation/sujets/{id_sujet}",
         response_model=SujetResponse,
         summary="Moderer un sujet (masquer/restaurer)")
def moderer_sujet(
    id_sujet: int,
    action:   ModerationAction,
    db:       Session = Depends(get_db)
):
    sujet = db.get(Sujet, id_sujet)
    if not sujet:
        raise HTTPException(404, "Sujet introuvable")
    sujet.statut   = action.statut
    sujet.date_modif = datetime.utcnow()
    db.commit()
    db.refresh(sujet)
    return sujet


@app.put("/forum/moderation/sujets/{id_sujet}/epingler",
         summary="Epingler ou desepingler un sujet")
def epingler_sujet(id_sujet: int, db: Session = Depends(get_db)):
    sujet = db.get(Sujet, id_sujet)
    if not sujet:
        raise HTTPException(404, "Sujet introuvable")
    sujet.est_epingle = not sujet.est_epingle
    db.commit()
    return {
        "message": "Sujet epingle" if sujet.est_epingle else "Sujet desepingle",
        "est_epingle": sujet.est_epingle
    }


@app.put("/forum/moderation/reponses/{id_reponse}",
         response_model=ReponseResponse,
         summary="Moderer une reponse (masquer/restaurer)")
def moderer_reponse(
    id_reponse: int,
    action:     ModerationAction,
    db:         Session = Depends(get_db)
):
    reponse = db.get(Reponse, id_reponse)
    if not reponse:
        raise HTTPException(404, "Reponse introuvable")
    reponse.statut    = action.statut
    reponse.date_modif = datetime.utcnow()
    db.commit()
    db.refresh(reponse)
    return reponse


# ══════════════════════════════════════════════════════════
# SIGNALEMENTS
# ══════════════════════════════════════════════════════════

@app.post("/forum/signalements", response_model=SignalementResponse,
          status_code=201, summary="Signaler un sujet ou une reponse")
def signaler(data: SignalementCreate, db: Session = Depends(get_db)):
    if not data.id_sujet and not data.id_reponse:
        raise HTTPException(400, "Precisez id_sujet ou id_reponse")

    signalement = Signalement(**data.model_dump())
    db.add(signalement)

    # Marquer automatiquement comme SIGNALE
    if data.id_sujet:
        sujet = db.get(Sujet, data.id_sujet)
        if sujet:
            sujet.statut = StatutPostEnum.SIGNALE
    if data.id_reponse:
        reponse = db.get(Reponse, data.id_reponse)
        if reponse:
            reponse.statut = StatutPostEnum.SIGNALE

    db.commit()
    db.refresh(signalement)
    return signalement


@app.get("/forum/signalements", response_model=List[SignalementResponse],
         summary="Liste des signalements non traites (moderateur)")
def list_signalements(
    traite: bool = False,
    db:     Session = Depends(get_db)
):
    return db.query(Signalement).filter(
        Signalement.traite == traite
    ).order_by(Signalement.date_signalement.desc()).all()


@app.put("/forum/signalements/{id_signalement}/traiter",
         summary="Marquer un signalement comme traite")
def traiter_signalement(id_signalement: int, db: Session = Depends(get_db)):
    s = db.get(Signalement, id_signalement)
    if not s:
        raise HTTPException(404, "Signalement introuvable")
    s.traite = True
    db.commit()
    return {"message": "Signalement marque comme traite"}


# ══════════════════════════════════════════════════════════
# STATISTIQUES
# ══════════════════════════════════════════════════════════

@app.get("/forum/stats", response_model=ForumStats,
         summary="Statistiques du forum")
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_sujets":   db.query(Sujet).count(),
        "sujets_resolus": db.query(Sujet).filter_by(est_resolu=True).count(),
        "total_reponses": db.query(Reponse).count(),
        "total_signalements_non_traites": db.query(Signalement).filter_by(traite=False).count(),
    }


@app.get("/health", tags=["Systeme"])
def health():
    return {"status": "ok", "service": "uniburkina-forum", "version": "1.0.0"}