# ==============================================================================
# service-ged/routes_extension.py — UniBurkina Hub — Extension v2.1
# AVOGAN Koudjo Augustin Sandaogo — INE N01213620231
#
# Ce fichier contient UNIQUEMENT les nouveaux endpoints à ajouter au
# service-ged existant. Inclure dans le main.py du service-ged avec :
#   from routes_extension import router as router_ext
#   app.include_router(router_ext)
#
# Nouveau endpoint :
#   PUT /ged/documents/{id}/classer  → modal validation avec métadonnées complètes
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import httpx, os

# ── Import des dépendances existantes du service-ged ─────────────────────────
# Ces imports supposent que le service-ged a : get_db, Document, engine
# Adapter selon votre structure si les noms diffèrent.

router = APIRouter()

API_AUTH = os.getenv("API_AUTH", "http://localhost:8001")

# Rôles autorisés à classer un document
ROLES_CLASSEMENT = {"ADMIN", "SOUS_ADMIN", "CHEF_DEPARTEMENT", "PRESIDENT"}


class ClassementIn(BaseModel):
    """Schéma de classement rigoureux d'un document après validation."""
    # Décision
    statut:          str             # VALIDE | REFUSE
    motif_refus:     Optional[str]   = None

    # Métadonnées de classement (obligatoires si VALIDE)
    titre:           Optional[str]   = None
    type_ressource:  Optional[str]   = None   # COURS | TD | EXAMEN | ARCHIVE
    id_filiere:      Optional[int]   = None
    id_module:       Optional[int]   = None
    description:     Optional[str]   = None
    annee_academique: Optional[str]  = None   # ex: "2025-2026"
    semestre:        Optional[str]   = None   # "S1" | "S2"

    # Notification
    notifier_soumetteur: bool        = True


async def _verifier_token(authorization: Optional[str]) -> Optional[dict]:
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


async def _notifier(id_user: int, titre: str, message: str, token: str):
    """Envoie une notification via service-auth."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{API_AUTH}/auth/notifications",
                json={"titre": titre, "message": message, "user_id": id_user},
                headers={"Authorization": f"Bearer {token}"}
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# PUT /ged/documents/{id}/classer
# Modal de validation avec classement complet des métadonnées
# ══════════════════════════════════════════════════════════════════════════════

# NOTE : Cet endpoint est conçu pour être copié/adapté dans le main.py
# du service-ged existant. Les imports (Document, get_db) viennent de
# votre code GED existant.

CLASSEMENT_ENDPOINT_CODE = '''
# ── Ajouter dans service-ged/main.py ──────────────────────────────────────────

class ClassementIn(BaseModel):
    statut:           str
    motif_refus:      Optional[str]  = None
    titre:            Optional[str]  = None
    type_ressource:   Optional[str]  = None
    id_filiere:       Optional[int]  = None
    id_module:        Optional[int]  = None
    description:      Optional[str]  = None
    annee_academique: Optional[str]  = None
    semestre:         Optional[str]  = None
    notifier_soumetteur: bool        = True

@app.put("/ged/documents/{id_doc}/classer",
         summary="Valider et classer rigoureusement un document avec toutes ses métadonnées")
async def classer_document(
    id_doc: int,
    data: ClassementIn,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint de classement complet (UC_05 enrichi).
    - Valide ou refuse le document
    - Met à jour TOUTES les métadonnées de classement
    - Notifie le soumetteur si demandé
    - Journalise l\'action
    """
    user = await verifier_token(authorization)
    if not user:
        raise HTTPException(401, "Authentification requise")
    if user.get("role") not in {"ADMIN", "SOUS_ADMIN", "CHEF_DEPARTEMENT", "PRESIDENT"}:
        raise HTTPException(403, "Action réservée aux sous-administrateurs")
    if data.statut not in ("VALIDE", "REFUSE"):
        raise HTTPException(400, "statut doit être VALIDE ou REFUSE")
    if data.statut == "REFUSE" and not (data.motif_refus or "").strip():
        raise HTTPException(400, "motif_refus obligatoire pour un refus")

    doc = db.query(Document).filter(Document.id_doc == id_doc).first()
    if not doc:
        raise HTTPException(404, "Document introuvable")

    # Mise à jour du statut et des métadonnées
    doc.statut     = data.statut
    doc.est_valide = (data.statut == "VALIDE")
    if data.statut == "REFUSE":
        doc.motif_refus = data.motif_refus
    if data.titre:          doc.titre          = data.titre
    if data.type_ressource: doc.type_ressource = data.type_ressource
    if data.id_filiere:     doc.id_filiere     = data.id_filiere
    if data.id_module:      doc.id_module      = data.id_module
    if data.description:    doc.description    = data.description
    # Champs optionnels selon votre modèle BDD
    # if data.annee_academique: doc.annee_academique = data.annee_academique
    # if data.semestre:         doc.semestre         = data.semestre

    db.commit()
    db.refresh(doc)

    # Notification soumetteur (background)
    token_str = (authorization or "").replace("Bearer ", "")
    if data.notifier_soumetteur and hasattr(doc, "id_soumis_par") and doc.id_soumis_par:
        if data.statut == "VALIDE":
            titre_notif = "Document validé et classé ✓"
            msg = (f"Votre document \\"{doc.titre}\\" a été validé et classé dans la catégorie "
                   f"{doc.type_ressource or \'\'} — filière ID {doc.id_filiere or \'N/A\'}.")
        else:
            titre_notif = "Document refusé"
            msg = (f"Votre document \\"{doc.titre}\\" a été refusé. "
                   f"Motif : {data.motif_refus}")
        background_tasks.add_task(
            notifier_utilisateur, doc.id_soumis_par, titre_notif, msg, token_str
        )

    return {
        "id_doc":        id_doc,
        "statut":        doc.statut,
        "est_valide":    doc.est_valide,
        "titre":         doc.titre,
        "type_ressource": doc.type_ressource,
        "id_filiere":    doc.id_filiere,
        "id_module":     doc.id_module,
        "motif_refus":   doc.motif_refus,
        "message":       f"Document {data.statut.lower()} et classé avec succès."
    }
'''

# Afficher le code à copier (utile pour le débogage / consultation)
print("=== routes_extension.py chargé ===")
print("Copiez CLASSEMENT_ENDPOINT_CODE dans votre service-ged/main.py")
print(CLASSEMENT_ENDPOINT_CODE)
