# ==============================================================================
# service-ged/main.py — UniBurkina Hub — Version 2.1
# AVOGAN Koudjo Augustin Sandaogo — INE N01213620231
# Ajouts v2.1 :
#   - PUT /ged/documents/{id}/classer  → classement rigoureux avec métadonnées
#   - Champ id_soumis_par dans upload  → pour notifications soumetteur
#   - Background tasks pour notifications via service-auth
# ==============================================================================

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import os, httpx, logging, uuid, hashlib
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("service-ged")

from models import (
    Base, Document, Planning, Annonce, StatutDocumentEnum, TypeRessourceEnum,
    VisibiliteDocumentEnum,
    DocumentCircuit, CircuitHistorique, StatutCircuitEnum, ActionCircuitEnum
)
from schemas import (
    DocumentCreate, DocumentResponse, DocumentValider,
    PlanningCreate, PlanningResponse,
    AnnonceCreate, AnnonceResponse,
    UploadResponse,
    CircuitCreate, CircuitResponse, ActionRequest
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


def _calculer_duree(depuis: datetime) -> int:
    """Retourne le nombre de secondes écoulées depuis une date."""
    return int((datetime.utcnow() - depuis).total_seconds())


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — Cloisonnement par service + code d'accès (Points 1, 4, 5)
# ══════════════════════════════════════════════════════════

def _hash_sha256(contenu: bytes) -> str:
    """Empreinte SHA-256 d'un fichier (Point 2 — intégrité entre versions)."""
    return hashlib.sha256(contenu).hexdigest()


# Seuil "échéance proche" pour le statut A_VENIR — ajustable si besoin.
SEUIL_ECHEANCE_PROCHE_HEURES = 48


def _statut_echeance(circuit: DocumentCircuit) -> Optional[str]:
    """
    Point 3 — indicateur de suivi des échéances, calculé à la volée
    (jamais stocké en base, donc toujours à jour au moment de la lecture).
    """
    if not circuit.date_limite:
        return None
    if circuit.statut in (StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE,
                          StatutCircuitEnum.PUBLIE):
        return None  # circuit clôturé : l'échéance n'a plus d'intérêt opérationnel
    maintenant = datetime.utcnow()
    if circuit.date_limite < maintenant:
        return "EN_RETARD"
    if (circuit.date_limite - maintenant).total_seconds() <= SEUIL_ECHEANCE_PROCHE_HEURES * 3600:
        return "A_VENIR"
    return "DANS_LES_TEMPS"


async def get_perimetre(authorization: Optional[str]) -> dict:
    """
    Interroge service-auth pour connaître le périmètre documentaire de
    l'utilisateur (poste_ids visibles, vision globale éventuelle sur une
    branche entière). Voir /auth/mon-perimetre côté service-auth.
    """
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


async def verifier_code_service(authorization: Optional[str], role_code: str, code: str) -> bool:
    """Délègue à service-auth la vérification du code de sécurité partagé du groupe."""
    if not authorization or not code or not role_code:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{API_AUTH}/auth/verifier-code-acces",
                json={"role_code": role_code, "code": code},
                headers={"Authorization": authorization},
            )
            return r.status_code == 200
    except Exception:
        return False


async def role_code_pour_poste(poste_id: Optional[str], authorization: Optional[str]) -> Optional[str]:
    """Retrouve le role_code du groupe de service auquel appartient un poste_id."""
    if not poste_id or not authorization:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{API_AUTH}/auth/groupe-de-poste/{poste_id}",
                headers={"Authorization": authorization},
            )
            if r.status_code == 200:
                return r.json().get("role_code")
    except Exception:
        pass
    return None


class AccesRefuseException(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=403, detail=message)


async def verifier_acces_document_administratif(
    doc, circuit, user: dict, authorization: Optional[str], code_acces: Optional[str]
):
    """
    Applique les règles validées :
    - ADMIN / SOUS_ADMIN : accès total (super-administrateurs plateforme).
    - Auteur du document : accès total, sans code (c'est le sien).
    - Étape courante ou étape déjà passée du circuit : lecture autorisée,
      étape future : refusée (Point 1).
    - Sinon (pas d'étape directe) : accès conditionné à l'appartenance au
      même groupe de service / à une branche supervisée (Point 4).
    - Dans tous les autres cas : le code de sécurité du service propriétaire
      du document est exigé (Point 5).
    """
    role = (user or {}).get("role")
    user_id = (user or {}).get("id")
    poste_id = (user or {}).get("poste_id")

    if role in ("ADMIN", "SOUS_ADMIN"):
        return

    if circuit and user_id and str(circuit.auteur_id) == str(user_id):
        return  # l'auteur consulte toujours librement son propre document

    exige_code = True

    if circuit and poste_id and poste_id in (circuit.circuit or []):
        idx = circuit.circuit.index(poste_id)
        if idx > circuit.niveau_index:
            raise AccesRefuseException(
                "Ce document n'est pas encore accessible : ce n'est pas encore votre étape dans le circuit."
            )
        # idx <= niveau_index -> étape courante (traitement) ou déjà validée (lecture seule) :
        # le circuit documentaire fait déjà foi de légitimité, aucun code supplémentaire requis.
        exige_code = False
    else:
        perimetre = await get_perimetre(authorization)
        owning_poste = circuit.auteur_poste_id if circuit else None
        if not owning_poste or owning_poste not in perimetre.get("poste_ids", []):
            raise AccesRefuseException(
                "Vous n'avez pas accès aux documents de ce service."
            )

    if exige_code and circuit:
        role_code = await role_code_pour_poste(circuit.auteur_poste_id, authorization)
        if role_code:
            if not code_acces:
                raise AccesRefuseException(
                    "Code de sécurité du service requis pour consulter ce document."
                )
            ok = await verifier_code_service(authorization, role_code, code_acces)
            if not ok:
                raise AccesRefuseException("Code de sécurité incorrect.")


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
    visibilite:     Optional[str]  = Form(None),     # AJOUT — PRIVE/PUBLIC, pertinent seulement si ADMINISTRATIF
    # v2.1 : champs optionnels pour soumission via service-ocr
    statut:         Optional[str]  = Form(None),     # forcer un statut (ex: VALIDE pour dépôt direct)
    est_valide:     Optional[str]  = Form(None),     # "true" | "false"
    texte_ocr:      Optional[str]  = Form(None),     # texte extrait par OCR
    description:    Optional[str]  = Form(None),
    id_soumis_par:  Optional[str]  = Form(None),     # AJOUT — UUID (string) de l'utilisateur soumetteur
    file:           UploadFile     = File(...),
    authorization:  Optional[str]  = Header(None),
    db:             Session        = Depends(get_db)
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification, et
    # id_soumis_par etait un champ de formulaire librement usurpable par
    # n'importe quel appelant. Desormais : authentification obligatoire, et
    # seul un ADMIN/SOUS_ADMIN (ou un appel sans utilisateur precis, ex :
    # pont service-ocr agissant pour le compte d'un etudiant deja identifie
    # en amont) peut renseigner un id_soumis_par different du sien.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    if id_soumis_par and user.get("role") not in ("ADMIN", "SOUS_ADMIN") \
            and id_soumis_par != user.get("id"):
        raise HTTPException(
            403,
            "Vous ne pouvez pas soumettre un document au nom d'un autre utilisateur."
        )
    if not id_soumis_par:
        id_soumis_par = user.get("id")

    valide, message = valider_fichier(file)
    if not valide:
        raise HTTPException(400, message)

    # AJOUT SECURITE UTS (Point 2) — empreinte SHA-256 calculée avant l'upload
    # (upload_fichier lit et consomme le flux ; on le relit ensuite depuis le
    # début grâce au seek(0) déjà fait dans storage_service).
    contenu_pour_hash = await file.read()
    hash_calcule = _hash_sha256(contenu_pour_hash)
    await file.seek(0)

    infos = await upload_fichier(file, bucket="documents",
                                  sous_dossier=type_ressource.lower())

    # Gérer le statut
    statut_final = StatutDocumentEnum.EN_ATTENTE
    if statut in ("VALIDE", "EN_ATTENTE", "REFUSE"):
        statut_final = StatutDocumentEnum(statut)

    est_valide_bool = (est_valide or "").lower() == "true" or statut == "VALIDE"

    # AJOUT — visibilite : seulement pour les documents ADMINISTRATIF, defaut PRIVE (le plus restrictif)
    visibilite_finale = None
    if type_ressource == "ADMINISTRATIF":
        visibilite_finale = (
            VisibiliteDocumentEnum(visibilite)
            if visibilite in ("PRIVE", "PUBLIC")
            else VisibiliteDocumentEnum.PRIVE
        )

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
        visibilite     = visibilite_finale,
        hash_fichier   = hash_calcule,
    )
    # AJOUT — le modèle Document a "uploaded_by" (UUID), pas "id_soumis_par" :
    # c'est la colonne qu'on avait déjà utilisée pour filtrer par utilisateur.
    if id_soumis_par:
        try:
            doc.uploaded_by = uuid.UUID(id_soumis_par)
        except ValueError:
            pass  # id_soumis_par invalide -> on n'assigne rien plutôt que de planter l'upload

    if est_valide_bool:
        doc.date_publication = datetime.utcnow()

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@app.get("/ged/documents", response_model=list[DocumentResponse],
         summary="Liste tous les documents (avec pagination)")
async def list_documents(
    statut:         Optional[str] = None,
    type_ressource: Optional[str] = None,
    id_filiere:     Optional[int] = None,
    id_module:      Optional[int] = None,
    id_soumis_par:  Optional[str] = None,
    ids_soumis_par: Optional[str] = None,
    page:           int = 1,
    limite:         int = 20,
    authorization:  Optional[str] = Header(None),
    db:             Session = Depends(get_db)
):
    # AJOUT SECURITE UTS — authentification obligatoire (absente auparavant).
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    query = db.query(Document)
    if statut:
        query = query.filter(Document.statut == statut)
    if type_ressource:
        query = query.filter(Document.type_ressource == type_ressource)
    if id_filiere:
        query = query.filter(Document.id_filiere == id_filiere)
    if id_module:
        query = query.filter(Document.id_module == id_module)
    if id_soumis_par:
        try:
            query = query.filter(Document.uploaded_by == uuid.UUID(id_soumis_par))
        except ValueError:
            raise HTTPException(400, "id_soumis_par doit etre un UUID valide")
    if ids_soumis_par:
        try:
            liste_ids = [uuid.UUID(i) for i in ids_soumis_par.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(400, "ids_soumis_par doit etre une liste d'UUIDs separes par des virgules")
        if not liste_ids:
            return []
        query = query.filter(Document.uploaded_by.in_(liste_ids))

    # AJOUT SECURITE UTS (Point 4) — la RECHERCHE/LISTE de documents
    # ADMINISTRATIFS est limitée aux documents dont l'auteur appartient au
    # même groupe de service (ou à une branche supervisée). ADMIN/SOUS_ADMIN
    # ne sont pas restreints. Les autres types (COURS/TD/EXAMEN/ARCHIVE)
    # gardent leur logique de visibilité académique existante, inchangée.
    if type_ressource == "ADMINISTRATIF" and user.get("role") not in ("ADMIN", "SOUS_ADMIN"):
        perimetre = await get_perimetre(authorization)
        postes_visibles = perimetre.get("poste_ids", [])
        if not postes_visibles:
            return []
        circuits_visibles = (
            db.query(DocumentCircuit.document_id)
            .filter(DocumentCircuit.auteur_poste_id.in_(postes_visibles))
        )
        ids_visibles = [row[0] for row in circuits_visibles.all()]
        # + ses propres documents administratifs, même sans circuit (brouillon)
        query = query.filter(
            (Document.id_doc.in_(ids_visibles)) |
            (Document.uploaded_by == uuid.UUID(user["id"]))
        )

    offset = (page - 1) * limite
    resultats = query.order_by(Document.date_soumission.desc()).offset(offset).limit(limite).all()

    # AJOUT SECURITE UTS — expose auteur_poste_id (via le dernier circuit) pour
    # que service-search puisse appliquer le même cloisonnement Point 4 en recherche.
    for doc in resultats:
        doc.auteur_poste_id = None
        if doc.type_ressource == TypeRessourceEnum.ADMINISTRATIF:
            dernier_circuit = (
                db.query(DocumentCircuit)
                .filter_by(document_id=doc.id_doc)
                .order_by(DocumentCircuit.date_envoi.desc())
                .first()
            )
            if dernier_circuit:
                doc.auteur_poste_id = dernier_circuit.auteur_poste_id

    return resultats


@app.get("/ged/documents/{id_doc}", response_model=DocumentResponse,
         summary="Détail d'un document")
async def get_document(
    id_doc: int,
    code_acces: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    # AJOUT SECURITE UTS — le cloisonnement ne s'applique qu'aux documents
    # administratifs (circuit documentaire). Les documents academiques
    # (COURS/TD/EXAMEN/ARCHIVE) gardent leur logique de visibilite existante.
    if doc.type_ressource == TypeRessourceEnum.ADMINISTRATIF:
        circuit = (
            db.query(DocumentCircuit)
            .filter_by(document_id=id_doc)
            .order_by(DocumentCircuit.date_envoi.desc())
            .first()
        )
        await verifier_acces_document_administratif(doc, circuit, user, authorization, code_acces)

    return doc


@app.get("/ged/documents/{id_doc}/telecharger",
         summary="Télécharger un document")
async def telecharger_document(
    id_doc: int,
    code_acces: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    from storage_service import url_presignee
    from fastapi.responses import RedirectResponse

    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    doc = db.get(Document, id_doc)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    if doc.type_ressource == TypeRessourceEnum.ADMINISTRATIF:
        circuit = (
            db.query(DocumentCircuit)
            .filter_by(document_id=id_doc)
            .order_by(DocumentCircuit.date_envoi.desc())
            .first()
        )
        await verifier_acces_document_administratif(doc, circuit, user, authorization, code_acces)

    if not fichier_existe(doc.chemin_fichier):
        raise HTTPException(404, "Fichier introuvable dans le stockage MinIO")
    # Génère une URL présignée MinIO (valable 60 min) et redirige
    url = url_presignee(doc.chemin_fichier, bucket="documents", expire_minutes=60)
    return RedirectResponse(url=url)


@app.put("/ged/documents/{id_doc}/valider",
         response_model=DocumentResponse,
         summary="Valider ou refuser un document (UC_05)")
async def valider_document(
    id_doc: int,
    data:   DocumentValider,
    authorization: Optional[str] = Header(None),
    db:     Session = Depends(get_db)
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification ni
    # controle de role (identique a /classer mais sans verification).
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Action réservée aux validateurs habilités")

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
async def supprimer_document(
    id_doc: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Suppression réservée aux administrateurs et validateurs habilités")

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
    id_soumis_par = str(doc.uploaded_by) if doc.uploaded_by else None

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
# CIRCUITS DOCUMENTAIRES — AJOUT UTS
# (endpoints manquants : /ged/circuits/mes-documents et /ged/circuits/recus
#  étaient définis dans routes.py mais ce routeur n'est jamais monté sur `app`,
#  ils sont donc réimplémentés ici pour être réellement exécutés)
# ==============================================================================

@app.post("/ged/circuits", response_model=CircuitResponse, status_code=201,
          summary="Créer un circuit documentaire (envoyer un document en circuit)")
async def creer_circuit(
    data: CircuitCreate,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    role = user.get("role", "")

    doc = db.get(Document, data.document_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    # AJOUT SECURITE UTS (Point 3) — l'échéance ne peut pas être dans le passé.
    if data.date_limite and data.date_limite < datetime.utcnow():
        raise HTTPException(400, "La date limite ne peut pas être antérieure à aujourd'hui.")

    # ── Validation du flux selon le rôle ──────────────────
    ROLES_ETUDIANTS      = {"ETUDIANT", "DELEGUE"}
    ROLES_ADMIN_CIRCUIT  = {"CABINET", "DIRECTEUR", "EMPLOYE", "SG", "VP_EIP", "VP_RCU", "PRESIDENT"}

    if role in ROLES_ETUDIANTS:
        if not data.circuit or len(data.circuit) != 1:
            raise HTTPException(400,
                "Un étudiant ne peut soumettre qu'au chef de département de son UFR (1 seul destinataire).")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{API_AUTH}/auth/chef-dept-de-etudiant/{user['id']}",
                    headers={"Authorization": authorization}
                )
                if r.status_code == 200:
                    chef = r.json()
                    if chef.get("poste_id") != data.circuit[0]:
                        raise HTTPException(403,
                            "Destinataire invalide : vous devez soumettre au chef de département de votre UFR.")
        except httpx.RequestError:
            pass  # Si service-auth indisponible, on laisse passer (dégradé)

    elif role in ROLES_ADMIN_CIRCUIT or role in {"ENSEIGNANT", "CHEF_DEPARTEMENT"}:
        if not data.circuit:
            raise HTTPException(400, "Le circuit doit contenir au moins un destinataire.")
        if not data.objet or not data.objet.strip():
            raise HTTPException(400, "L'objet du document est obligatoire pour un circuit administratif.")

    elif role not in {"ADMIN", "SOUS_ADMIN"}:
        raise HTTPException(403, "Votre rôle ne permet pas de créer un circuit documentaire.")

    circuit = DocumentCircuit(
        document_id=data.document_id,
        auteur_id=uuid.UUID(user["id"]),
        auteur_poste_id=user.get("poste_id"),
        circuit=data.circuit,
        niveau_index=0,
        statut=StatutCircuitEnum.EN_ATTENTE,
        objet=data.objet,
        commentaire_init=data.commentaire_init,
        date_limite=data.date_limite,
    )
    db.add(circuit); db.flush()

    histo = CircuitHistorique(
        circuit_id=circuit.id,
        acteur_id=uuid.UUID(user["id"]),
        acteur_poste_id=user.get("poste_id"),
        acteur_nom=f"{user.get('prenom', '')} {user.get('nom', '')}".strip(),
        action=ActionCircuitEnum.ENVOYE,
        niveau_avant=None,
        niveau_apres=0,
        commentaire=data.commentaire_init,
        hash_fichier=doc.hash_fichier,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(histo)
    db.commit(); db.refresh(circuit)
    return circuit


@app.post("/ged/circuits/{circuit_id}/action",
          summary="Agir sur un circuit : transmettre / valider / rejeter / retourner / commenter")
async def action_circuit(
    circuit_id: int,
    data: ActionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    poste_id = user.get("poste_id")

    circuit = db.get(DocumentCircuit, circuit_id)
    if not circuit:
        raise HTTPException(404, "Circuit introuvable")
    if circuit.statut in (StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE,
                          StatutCircuitEnum.PUBLIE):
        raise HTTPException(400, "Ce circuit est déjà clôturé")

    if (poste_id and
            circuit.niveau_index < len(circuit.circuit) and
            circuit.circuit[circuit.niveau_index] != poste_id and
            data.action != ActionCircuitEnum.COMMENTE):
        raise HTTPException(403, "Ce n'est pas votre tour dans ce circuit")

    niveau_avant = circuit.niveau_index
    niveau_apres = niveau_avant
    duree        = _calculer_duree(circuit.date_derniere_action)

    if data.etapes_ajout and data.action == ActionCircuitEnum.TRANSMIS:
        nouvelle_liste = list(circuit.circuit)
        pos_insertion  = niveau_avant + 1
        for i, poste in enumerate(data.etapes_ajout):
            nouvelle_liste.insert(pos_insertion + i, poste)
        circuit.circuit = nouvelle_liste

    if data.action == ActionCircuitEnum.TRANSMIS:
        niveau_apres = niveau_avant + 1
        if niveau_apres >= len(circuit.circuit):
            circuit.statut       = StatutCircuitEnum.VALIDE
            circuit.date_cloture = datetime.utcnow()
        else:
            circuit.statut       = StatutCircuitEnum.EN_ATTENTE
            circuit.niveau_index = niveau_apres

    elif data.action == ActionCircuitEnum.VALIDE:
        circuit.statut       = StatutCircuitEnum.VALIDE
        circuit.date_cloture = datetime.utcnow()
        niveau_apres         = niveau_avant

    elif data.action == ActionCircuitEnum.REJETE:
        circuit.statut       = StatutCircuitEnum.REJETE
        circuit.date_cloture = datetime.utcnow()
        niveau_apres         = niveau_avant

    elif data.action == ActionCircuitEnum.RETOURNE:
        niveau_apres = max(0, niveau_avant - 1)
        circuit.niveau_index = niveau_apres
        circuit.statut        = StatutCircuitEnum.EN_ATTENTE

    elif data.action == ActionCircuitEnum.COMMENTE:
        pass

    circuit.date_derniere_action = datetime.utcnow()

    histo = CircuitHistorique(
        circuit_id=circuit_id,
        acteur_id=uuid.UUID(user["id"]),
        acteur_poste_id=poste_id,
        acteur_nom=f"{user.get('prenom', '')} {user.get('nom', '')}".strip(),
        action=data.action,
        niveau_avant=niveau_avant,
        niveau_apres=niveau_apres,
        commentaire=data.commentaire,
        duree_etape_secondes=duree,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(histo)
    db.commit(); db.refresh(circuit)

    token_str = (authorization or "").replace("Bearer ", "")
    if circuit.statut in (StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE):
        statut_label = "validé" if circuit.statut == StatutCircuitEnum.VALIDE else "rejeté"
        background_tasks.add_task(
            notifier_utilisateur,
            str(circuit.auteur_id),
            f"Circuit documentaire {statut_label}",
            f"Votre document (circuit #{circuit_id}) a été {statut_label}. "
            f"Commentaire : {data.commentaire or 'aucun'}",
            token_str
        )

    return {
        "circuit_id":   circuit_id,
        "statut":       circuit.statut,
        "niveau_index": circuit.niveau_index,
        "action":       data.action,
        "message":      f"Action '{data.action}' enregistrée avec succès."
    }


@app.get("/ged/circuits/mes-documents", response_model=List[CircuitResponse],
         summary="Historique des circuits créés par l'utilisateur connecté")
async def mes_circuits(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    circuits = (
        db.query(DocumentCircuit)
        .filter_by(auteur_id=uuid.UUID(user["id"]))
        .order_by(DocumentCircuit.date_envoi.desc())
        .all()
    )
    for c in circuits:
        c.statut_echeance = _statut_echeance(c)
    return circuits


@app.get("/ged/circuits/recus", response_model=List[CircuitResponse],
         summary="Documents en attente d'action pour l'utilisateur connecté")
async def circuits_recus(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Retourne les circuits dont le destinataire au niveau_index courant
    correspond au poste_id de l'utilisateur connecté.
    """
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    poste_id = user.get("poste_id")
    if not poste_id:
        return []

    circuits = (
        db.query(DocumentCircuit)
        .filter(DocumentCircuit.statut.in_(
            [StatutCircuitEnum.EN_ATTENTE, StatutCircuitEnum.EN_COURS]
        ))
        .all()
    )
    recus = [
        c for c in circuits
        if c.niveau_index < len(c.circuit) and c.circuit[c.niveau_index] == poste_id
    ]
    for c in recus:
        c.statut_echeance = _statut_echeance(c)
    return recus


@app.get("/ged/circuits/en-retard", response_model=List[CircuitResponse],
         summary="Liste des circuits en retard (échéance dépassée, non clôturés)")
async def circuits_en_retard(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Point 3 — suivi des échéances. Un ADMIN/SOUS_ADMIN voit tous les circuits
    en retard ; les autres utilisateurs ne voient que ceux qu'ils sont déjà
    autorisés à consulter (auteur, étape courante/passée, ou groupe de service —
    mêmes règles que verifier_acces_document_administratif, Point 1/4).

    IMPORTANT : cette route DOIT rester déclarée avant
    /ged/circuits/{circuit_id} ci-dessous, sinon FastAPI tente de faire
    correspondre "en-retard" au paramètre circuit_id et renvoie 422.
    """
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    maintenant = datetime.utcnow()
    circuits = (
        db.query(DocumentCircuit)
        .filter(
            DocumentCircuit.date_limite.isnot(None),
            DocumentCircuit.date_limite < maintenant,
            DocumentCircuit.statut.notin_([
                StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE, StatutCircuitEnum.PUBLIE
            ]),
        )
        .order_by(DocumentCircuit.date_limite.asc())
        .all()
    )

    role = user.get("role")
    if role not in ("ADMIN", "SOUS_ADMIN"):
        poste_id = user.get("poste_id")
        user_id = user.get("id")
        perimetre = await get_perimetre(authorization)
        postes_visibles = set(perimetre.get("poste_ids", []))

        def _visible(c: DocumentCircuit) -> bool:
            if user_id and str(c.auteur_id) == str(user_id):
                return True
            if poste_id and poste_id in (c.circuit or []):
                idx = c.circuit.index(poste_id)
                return idx <= c.niveau_index
            return c.auteur_poste_id in postes_visibles

        circuits = [c for c in circuits if _visible(c)]

    for c in circuits:
        c.statut_echeance = "EN_RETARD"
    return circuits


@app.get("/ged/circuits/{circuit_id}", response_model=CircuitResponse,
         summary="Détail d'un circuit avec historique complet")
async def get_circuit(
    circuit_id: int,
    code_acces: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    circuit = db.get(DocumentCircuit, circuit_id)
    if not circuit:
        raise HTTPException(404, "Circuit introuvable")

    # AJOUT SECURITE UTS (Point 1) — meme regle que pour le document : seules
    # l'etape courante, les etapes deja validees (lecture seule) et l'auteur
    # peuvent consulter le circuit et son historique complet.
    doc = db.get(Document, circuit.document_id)
    if doc is not None:
        await verifier_acces_document_administratif(doc, circuit, user, authorization, code_acces)

    circuit.statut_echeance = _statut_echeance(circuit)
    return circuit


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — endpoints manquants : ils existaient dans
# routes.py (jamais monté sur `app`, voir plus haut) mais pas dans main.py,
# ils étaient donc totalement inaccessibles. Réimplémentés ici, avec
# contrôle d'accès (seule l'étape courante peut modifier/remplacer) et
# traçabilité renforcée (hash, IP, user-agent — Point 2).
# ══════════════════════════════════════════════════════════

class ModifierDocumentRequest(BaseModel):
    titre:          Optional[str] = None
    type_ressource: Optional[str] = None
    id_module:      Optional[int] = None
    id_filiere:     Optional[int] = None
    commentaire:    Optional[str] = None


def _verifier_etape_courante(circuit: DocumentCircuit, user: dict):
    """Seule l'étape courante (ou l'auteur) peut modifier/remplacer un document en circuit."""
    poste_id = user.get("poste_id")
    user_id  = user.get("id")
    if user_id and str(circuit.auteur_id) == str(user_id):
        return
    if not (poste_id and circuit.niveau_index < len(circuit.circuit)
            and circuit.circuit[circuit.niveau_index] == poste_id):
        raise HTTPException(403, "Seule l'étape courante du circuit peut modifier ce document.")


@app.put("/ged/circuits/{circuit_id}/modifier",
         summary="Modifier les métadonnées du document à l'étape courante")
async def modifier_document_circuit(
    circuit_id: int,
    data: ModifierDocumentRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    circuit = db.get(DocumentCircuit, circuit_id)
    if not circuit:
        raise HTTPException(404, "Circuit introuvable")
    if circuit.statut in (StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE):
        raise HTTPException(400, "Impossible de modifier un circuit clôturé")
    _verifier_etape_courante(circuit, user)

    doc = db.get(Document, circuit.document_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    for field, value in data.model_dump(exclude={"commentaire"}, exclude_none=True).items():
        setattr(doc, field, value)
    db.commit()

    histo = CircuitHistorique(
        circuit_id=circuit_id,
        acteur_id=uuid.UUID(user["id"]),
        acteur_poste_id=user.get("poste_id"),
        acteur_nom=f"{user.get('prenom', '')} {user.get('nom', '')}".strip(),
        action=ActionCircuitEnum.MODIFIE,
        niveau_avant=circuit.niveau_index,
        niveau_apres=circuit.niveau_index,
        commentaire=data.commentaire,
        duree_etape_secondes=_calculer_duree(circuit.date_derniere_action),
    )
    db.add(histo)
    circuit.date_derniere_action = datetime.utcnow()
    db.commit()

    return {"message": "Document modifié avec succès.", "id_doc": doc.id_doc}


@app.put("/ged/circuits/{circuit_id}/remplacer-fichier",
         summary="Remplacer le fichier du document dans le circuit")
async def remplacer_fichier_circuit(
    circuit_id: int,
    file: UploadFile = File(...),
    commentaire: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")

    circuit = db.get(DocumentCircuit, circuit_id)
    if not circuit:
        raise HTTPException(404, "Circuit introuvable")
    if circuit.statut in (StatutCircuitEnum.VALIDE, StatutCircuitEnum.REJETE):
        raise HTTPException(400, "Impossible de modifier un circuit clôturé")
    _verifier_etape_courante(circuit, user)

    doc = db.get(Document, circuit.document_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")

    valide, message = valider_fichier(file)
    if not valide:
        raise HTTPException(400, message)

    # AJOUT SECURITE UTS — hash calculé AVANT stockage pour la traçabilité
    contenu = await file.read()
    nouveau_hash = _hash_sha256(contenu)
    await file.seek(0)

    ancien_chemin = doc.chemin_fichier
    infos = await upload_fichier(file, bucket="documents")
    doc.chemin_fichier = infos["chemin_fichier"]
    doc.nom_fichier    = infos["nom_original"]
    doc.taille_fichier = infos["taille_fichier"]
    doc.type_mime      = infos["type_mime"]
    doc.hash_fichier   = nouveau_hash
    db.commit()

    histo = CircuitHistorique(
        circuit_id=circuit_id,
        acteur_id=uuid.UUID(user["id"]),
        acteur_poste_id=user.get("poste_id"),
        acteur_nom=f"{user.get('prenom', '')} {user.get('nom', '')}".strip(),
        action=ActionCircuitEnum.REMPLACE,
        niveau_avant=circuit.niveau_index,
        niveau_apres=circuit.niveau_index,
        nouveau_fichier=infos["chemin_fichier"],
        hash_fichier=nouveau_hash,
        commentaire=commentaire or f"Fichier remplacé (ancien : {ancien_chemin})",
        duree_etape_secondes=_calculer_duree(circuit.date_derniere_action),
    )
    db.add(histo)
    circuit.date_derniere_action = datetime.utcnow()
    db.commit()

    return {"message": "Fichier remplacé avec succès.", "nouveau_chemin": infos["chemin_fichier"],
            "hash_fichier": nouveau_hash}


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
    authorization: Optional[str] = Header(None),
    db:         Session        = Depends(get_db)
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Publication de planning réservée aux personnels habilités")

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
    # Lecture volontairement laissée publique (plannings destinés à être
    # consultés par les étudiants/enseignants sans friction) — inchangé.
    query = db.query(Planning)
    if id_filiere:
        query = query.filter(Planning.id_filiere == id_filiere)
    return query.order_by(Planning.date_envoi.desc()).all()


@app.put("/ged/plannings/{id_planning}/publier",
         response_model=PlanningResponse,
         summary="Publier un planning")
async def publier_planning(
    id_planning: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Publication de planning réservée aux personnels habilités")

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
async def create_annonce(
    data: AnnonceCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification :
    # n'importe qui pouvait créer une annonce institutionnelle.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Création d'annonce réservée aux personnels habilités")

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
    # Lecture volontairement laissée publique (annonces déjà filtrées sur
    # est_publiee=True) — inchangé.
    query = db.query(Annonce).filter(Annonce.est_publiee == True)
    if id_filiere:
        query = query.filter(Annonce.id_filiere == id_filiere)
    if id_univ:
        query = query.filter(Annonce.id_univ == id_univ)
    return query.order_by(Annonce.date_creation.desc()).all()


@app.put("/ged/annonces/{id_annonce}/publier",
         response_model=AnnonceResponse,
         summary="Publier une annonce")
async def publier_annonce(
    id_annonce: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    # AJOUT SECURITE UTS — cet endpoint n'avait aucune authentification.
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in ROLES_CLASSEMENT:
        raise HTTPException(403, "Publication d'annonce réservée aux personnels habilités")

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
