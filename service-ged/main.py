# ==============================================================================
# service-ged/main.py — UniBurkina Hub — Version 2.1
# AVOGAN Koudjo Augustin Sandaogo — INE N01213620231
# Ajouts v2.1 :
#   - PUT /ged/documents/{id}/classer  → classement rigoureux avec métadonnées
#   - Champ id_soumis_par dans upload  → pour notifications soumetteur
#   - Background tasks pour notifications via service-auth
# ==============================================================================

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import os, httpx, logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("service-ged")

from models import Base, Document, Planning, Annonce, StatutDocumentEnum, TypeRessourceEnum
from schemas import (
    DocumentCreate, DocumentResponse, DocumentValider,
    PlanningCreate, PlanningResponse,
    AnnonceCreate, AnnonceResponse,
    UploadResponse
)
from storage_service import (
    init_storage, upload_fichier, supprimer_fichier,
    fichier_existe, lister_fichiers, valider_fichier
)

# ── Config ─────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://uniburkina_admin:UTS_Burkina2025!@localhost:5432/uniburkina_db"
)
API_AUTH = os.getenv("API_AUTH", "http://localhost:8001")

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
init_storage()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Application FastAPI ─────────────────────────────────────
app = FastAPI(
    title="UniBurkina Hub — Service GED",
    description="Gestion Electronique de Documents academiques v2.1",
    version="2.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000", "http://localhost:8001",
        "http://localhost:8002", "http://localhost:8003",
        "http://localhost:8004", "http://localhost:8005",
        "http://127.0.0.1:8000", "http://127.0.0.1:8001",
        "http://127.0.0.1:8002", "http://127.0.0.1:8003",
        "http://127.0.0.1:8004", "http://127.0.0.1:8005",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rôles autorisés au classement ──────────────────────────
ROLES_CLASSEMENT = {"ADMIN", "SOUS_ADMIN", "CHEF_DEPARTEMENT", "PRESIDENT"}


# ==============================================================================
# HELPERS
# ==============================================================================

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


async def notifier_utilisateur(
    id_utilisateur: int, titre_notif: str, message: str, token: str
):
    """Envoie une notification via service-auth (background task)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{API_AUTH}/auth/notifications",
                json={
                    "titre":   titre_notif,
                    "message": message,
                    "user_id": id_utilisateur,
                },
                headers={"Authorization": f"Bearer {token}"}
            )
    except Exception as e:
        log.warning(f"Notification échouée pour user {id_utilisateur} : {e}")


# ==============================================================================
# DOCUMENTS
# ==============================================================================

@app.post("/ged/documents/upload", response_model=DocumentResponse,
          status_code=201, summary="Uploader un document (PDF/Image)")
async def upload_document(
    titre:          str            = Form(...),
    type_ressource: str            = Form(...),
    id_module:      Optional[int]  = Form(None),
    id_filiere:     Optional[int]  = Form(None),
    id_univ:        Optional[int]  = Form(None),
    # v2.1 : champs optionnels pour soumission via service-ocr
    statut:         Optional[str]  = Form(None),     # forcer un statut (ex: VALIDE pour dépôt direct)
    est_valide:     Optional[str]  = Form(None),     # "true" | "false"
    texte_ocr:      Optional[str]  = Form(None),     # texte extrait par OCR
    description:    Optional[str]  = Form(None),
    id_soumis_par:  Optional[int]  = Form(None),     # id utilisateur soumetteur
    file:           UploadFile     = File(...),
    db:             Session        = Depends(get_db)
):
    valide, message = valider_fichier(file)
    if not valide:
        raise HTTPException(400, message)

    infos = await upload_fichier(file, bucket="documents",
                                  sous_dossier=type_ressource.lower())

    # Gérer le statut
    statut_final = StatutDocumentEnum.EN_ATTENTE
    if statut in ("VALIDE", "EN_ATTENTE", "REFUSE"):
        statut_final = StatutDocumentEnum(statut)

    est_valide_bool = (est_valide or "").lower() == "true" or statut == "VALIDE"

    doc = Document(
        titre          = titre,
        type_ressource = TypeRessourceEnum(type_ressource),
        chemin_fichier = infos["chemin_fichier"],
        nom_fichier    = infos["nom_original"],
        taille_fichier = infos["taille_fichier"],
        type_mime      = infos["type_mime"],
        id_module      = id_module,
        id_filiere     = id_filiere,
        id_univ        = id_univ,
        statut         = statut_final,
        est_valide     = est_valide_bool,
        texte_ocr      = texte_ocr,
        # Stocker l'id soumetteur si votre modèle a ce champ
        # id_soumis_par = id_soumis_par,
    )
    # Si votre modèle Document a id_soumis_par, décommentez la ligne ci-dessus
    # et commentez la ligne suivante :
    if id_soumis_par and hasattr(doc, "id_soumis_par"):
        doc.id_soumis_par = id_soumis_par

    if est_valide_bool:
        doc.date_publication = datetime.utcnow()

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@app.get("/ged/documents", response_model=list[DocumentResponse],
         summary="Liste tous les documents (avec pagination)")
def list_documents(
    statut:         Optional[str] = None,
    type_ressource: Optional[str] = None,
    id_filiere:     Optional[int] = None,
    id_module:      Optional[int] = None,
    page:           int = 1,
    limite:         int = 20,
    db:             Session = Depends(get_db)
):
    query = db.query(Document)
    if statut:
        query = query.filter(Document.statut == statut)
    if type_ressource:
        query = query.filter(Document.type_ressource == type_ressource)
    if id_filiere:
        query = query.filter(Document.id_filiere == id_filiere)
    if id_module:
        query = query.filter(Document.id_module == id_module)

    offset = (page - 1) * limite
    return query.order_by(Document.date_soumission.desc()).offset(offset).limit(limite).all()


@app.get("/ged/documents/{id_doc}", response_model=DocumentResponse,
         summary="Détail d'un document")
def get_document(id_doc: int, db: Session = Depends(get_db)):
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    return doc


@app.get("/ged/documents/{id_doc}/telecharger",
         summary="Télécharger un document")
def telecharger_document(id_doc: int, db: Session = Depends(get_db)):
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    if not fichier_existe(doc.chemin_fichier):
        raise HTTPException(404, "Fichier physique introuvable")
    return FileResponse(
        path=doc.chemin_fichier,
        filename=doc.nom_fichier or f"document_{id_doc}",
        media_type=doc.type_mime or "application/octet-stream"
    )


@app.put("/ged/documents/{id_doc}/valider",
         response_model=DocumentResponse,
         summary="Valider ou refuser un document (UC_05)")
def valider_document(
    id_doc: int,
    data:   DocumentValider,
    db:     Session = Depends(get_db)
):
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    doc.statut      = data.statut
    doc.motif_refus = data.motif_refus

    if data.statut == StatutDocumentEnum.VALIDE:
        doc.est_valide       = True
        doc.date_publication = datetime.utcnow()
    else:
        doc.est_valide = False

    # v2.1 : mise à jour métadonnées si fournies
    if hasattr(data, "titre")          and data.titre:          doc.titre          = data.titre
    if hasattr(data, "type_ressource") and data.type_ressource: doc.type_ressource = TypeRessourceEnum(data.type_ressource)
    if hasattr(data, "id_filiere")     and data.id_filiere:     doc.id_filiere     = data.id_filiere
    if hasattr(data, "id_module")      and data.id_module:      doc.id_module      = data.id_module

    db.commit()
    db.refresh(doc)
    return doc


@app.delete("/ged/documents/{id_doc}",
            summary="Supprimer un document")
def supprimer_document(id_doc: int, db: Session = Depends(get_db)):
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    supprimer_fichier(doc.chemin_fichier)
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.titre}' supprimé"}


# ══════════════════════════════════════════════════════════
# ENDPOINT PONT — Injection texte OCR depuis service-ocr
# ══════════════════════════════════════════════════════════

class TexteOCRUpdate(BaseModel):
    texte_ocr: str

@app.patch("/ged/documents/{id_doc}/texte-ocr",
           response_model=DocumentResponse,
           summary="Mettre à jour le texte OCR d'un document (appel interne)")
def update_texte_ocr(
    id_doc: int,
    data:   TexteOCRUpdate,
    db:     Session = Depends(get_db)
):
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    doc.texte_ocr = data.texte_ocr
    db.commit()
    db.refresh(doc)
    return doc


# ==============================================================================
# NOUVEAU v2.1 — PUT /ged/documents/{id}/classer
# Classement rigoureux avec toutes les métadonnées + notification soumetteur
# ==============================================================================

class ClassementIn(BaseModel):
    """Schéma complet de classement d'un document après décision de validation."""
    # Décision obligatoire
    statut:           str                   # "VALIDE" | "REFUSE"
    motif_refus:      Optional[str]  = None  # Obligatoire si REFUSE

    # Métadonnées de classement (renseignées par le validateur)
    titre:            Optional[str]  = None
    type_ressource:   Optional[str]  = None  # COURS | TD | EXAMEN | ARCHIVE
    id_filiere:       Optional[int]  = None
    id_module:        Optional[int]  = None
    description:      Optional[str]  = None
    annee_academique: Optional[str]  = None  # ex: "2025-2026"
    semestre:         Optional[str]  = None  # "S1" | "S2"

    # Options
    notifier_soumetteur: bool        = True


@app.put("/ged/documents/{id_doc}/classer",
         response_model=DocumentResponse,
         summary="Valider et classer rigoureusement un document (UC_05 enrichi)")
async def classer_document(
    id_doc:           int,
    data:             ClassementIn,
    background_tasks: BackgroundTasks,
    authorization:    Optional[str] = Header(None),
    db:               Session       = Depends(get_db)
):
    """
    Endpoint de classement complet — Version enrichie de UC_05.

    Actions effectuées :
    - Valide ou refuse le document
    - Met à jour TOUTES les métadonnées de classement (titre, type, filière, module...)
    - Notifie le soumetteur si demandé (via service-auth /auth/notifications)
    - Journalise l'action dans les logs

    Accès réservé : ADMIN, SOUS_ADMIN, CHEF_DEPARTEMENT, PRESIDENT
    """
    # Vérification du token
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise — fournir un Bearer token valide")

    role = user.get("role", "")
    if role not in ROLES_CLASSEMENT:
        raise HTTPException(
            403,
            f"Action réservée aux sous-administrateurs et chefs de département "
            f"(rôle actuel : {role})"
        )

    # Validation des données
    if data.statut not in ("VALIDE", "REFUSE"):
        raise HTTPException(400, "statut doit être VALIDE ou REFUSE")
    if data.statut == "REFUSE" and not (data.motif_refus or "").strip():
        raise HTTPException(400, "motif_refus obligatoire pour un refus — veuillez préciser le motif")

    # Récupération du document
    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, f"Document {id_doc} introuvable")

    # ── Mise à jour du statut ──────────────────────────────
    doc.statut     = StatutDocumentEnum(data.statut)
    doc.est_valide = (data.statut == "VALIDE")

    if data.statut == "VALIDE":
        doc.date_publication = datetime.utcnow()
        doc.motif_refus      = None
    else:
        doc.motif_refus      = data.motif_refus
        doc.date_publication = None

    # ── Mise à jour des métadonnées de classement ─────────
    if data.titre          is not None: doc.titre          = data.titre
    if data.id_filiere     is not None: doc.id_filiere     = data.id_filiere
    if data.id_module      is not None: doc.id_module      = data.id_module
    if data.description    is not None and hasattr(doc, "description"):
        doc.description = data.description

    if data.type_ressource is not None:
        try:
            doc.type_ressource = TypeRessourceEnum(data.type_ressource)
        except ValueError:
            log.warning(f"type_ressource invalide : {data.type_ressource} — ignoré")

    # Champs optionnels selon votre modèle BDD
    if data.annee_academique is not None and hasattr(doc, "annee_academique"):
        doc.annee_academique = data.annee_academique
    if data.semestre         is not None and hasattr(doc, "semestre"):
        doc.semestre = data.semestre

    db.commit()
    db.refresh(doc)

    log.info(
        f"Document {id_doc} classé '{data.statut}' par {user.get('username', 'N/A')} "
        f"(rôle: {role}) — titre: {doc.titre}"
    )

    # ── Notification soumetteur (background) ──────────────
    token_str = (authorization or "").replace("Bearer ", "")
    id_soumis_par = getattr(doc, "id_soumis_par", None)

    if data.notifier_soumetteur and id_soumis_par and token_str:
        if data.statut == "VALIDE":
            titre_notif = "Document validé et classé ✓"
            msg = (
                f"Votre document \"{doc.titre}\" a été validé et classé "
                f"dans la catégorie {doc.type_ressource.value if doc.type_ressource else 'N/A'}."
                f" Il est maintenant accessible aux étudiants de votre filière."
            )
        else:
            titre_notif = "Document refusé"
            msg = (
                f"Votre document \"{doc.titre}\" a été refusé par le validateur. "
                f"Motif : {data.motif_refus}. "
                f"Vous pouvez le corriger et le resoumettre."
            )
        background_tasks.add_task(
            notifier_utilisateur, id_soumis_par, titre_notif, msg, token_str
        )

    return doc


# ==============================================================================
# PLANNINGS
# ==============================================================================

@app.post("/ged/plannings/upload", response_model=PlanningResponse,
          status_code=201, summary="Uploader un planning")
async def upload_planning(
    semaine:    str            = Form(...),
    titre:      str            = Form(...),
    id_filiere: Optional[int]  = Form(None),
    id_univ:    Optional[int]  = Form(None),
    file:       UploadFile     = File(...),
    db:         Session        = Depends(get_db)
):
    infos = await upload_fichier(file, bucket="plannings")
    planning = Planning(
        semaine    = semaine,
        titre      = titre,
        fichier_url = infos["chemin_fichier"],
        id_filiere = id_filiere,
        id_univ    = id_univ
    )
    db.add(planning)
    db.commit()
    db.refresh(planning)
    return planning


@app.get("/ged/plannings", response_model=list[PlanningResponse],
         summary="Liste des plannings")
def list_plannings(
    id_filiere: Optional[int] = None,
    db:         Session = Depends(get_db)
):
    query = db.query(Planning)
    if id_filiere:
        query = query.filter(Planning.id_filiere == id_filiere)
    return query.order_by(Planning.date_envoi.desc()).all()


@app.put("/ged/plannings/{id_planning}/publier",
         response_model=PlanningResponse,
         summary="Publier un planning")
def publier_planning(id_planning: int, db: Session = Depends(get_db)):
    planning = db.get(Planning, id_planning)
    if not planning:
        raise HTTPException(404, "Planning introuvable")
    planning.est_publie = True
    db.commit()
    db.refresh(planning)
    return planning


# ==============================================================================
# ANNONCES
# ==============================================================================

@app.post("/ged/annonces", response_model=AnnonceResponse,
          status_code=201, summary="Créer une annonce")
def create_annonce(data: AnnonceCreate, db: Session = Depends(get_db)):
    annonce = Annonce(**data.model_dump())
    db.add(annonce)
    db.commit()
    db.refresh(annonce)
    return annonce


@app.get("/ged/annonces", response_model=list[AnnonceResponse],
         summary="Liste des annonces publiées")
def list_annonces(
    id_filiere: Optional[int] = None,
    id_univ:    Optional[int] = None,
    db:         Session = Depends(get_db)
):
    query = db.query(Annonce).filter(Annonce.est_publiee == True)
    if id_filiere:
        query = query.filter(Annonce.id_filiere == id_filiere)
    if id_univ:
        query = query.filter(Annonce.id_univ == id_univ)
    return query.order_by(Annonce.date_creation.desc()).all()


@app.put("/ged/annonces/{id_annonce}/publier",
         response_model=AnnonceResponse,
         summary="Publier une annonce")
def publier_annonce(id_annonce: int, db: Session = Depends(get_db)):
    annonce = db.get(Annonce, id_annonce)
    if not annonce:
        raise HTTPException(404, "Annonce introuvable")
    annonce.est_publiee = True
    db.commit()
    db.refresh(annonce)
    return annonce


# ==============================================================================
# STATISTIQUES
# ==============================================================================

@app.get("/ged/stats", summary="Statistiques globales GED")
def get_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(Document).count()
    valides = db.query(Document).filter_by(est_valide=True).count()
    attente = db.query(Document).filter(
                  Document.statut == StatutDocumentEnum.EN_ATTENTE).count()
    refuses = db.query(Document).filter(
                  Document.statut == StatutDocumentEnum.REFUSE).count()

    # Répartition par type
    types = {}
    for t in TypeRessourceEnum:
        types[t.value] = db.query(Document).filter(
            Document.type_ressource == t).count()

    return {
        "total_documents":    total,
        "documents_valides":  valides,
        "documents_attente":  attente,
        "documents_refuses":  refuses,
        "total_plannings":    db.query(Planning).count(),
        "total_annonces":     db.query(Annonce).filter_by(est_publiee=True).count(),
        "fichiers_stockes":   len(lister_fichiers("documents")),
        "repartition_types":  types,
    }


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health", tags=["Système"])
def health():
    return {
        "status":   "ok",
        "service":  "uniburkina-ged",
        "version":  "2.1.0",
        "nouveautes": ["POST /ged/documents/upload (statut + texte_ocr)", "PUT /ged/documents/{id}/classer"]
    }
