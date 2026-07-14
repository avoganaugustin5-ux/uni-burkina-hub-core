from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

# ── Enums ──────────────────────────────────────────────────
class TypeRessourceEnum(str, Enum):
    COURS         = "COURS"
    TD            = "TD"
    EXAMEN        = "EXAMEN"
    ARCHIVE       = "ARCHIVE"
    ADMINISTRATIF = "ADMINISTRATIF"  # AJOUT UTS — documents du circuit documentaire

class StatutDocumentEnum(str, Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REFUSE     = "REFUSE"

# ── AJOUT — Visibilité d'un document administratif ────────
class VisibiliteDocumentEnum(str, Enum):
    PRIVE  = "PRIVE"
    PUBLIC = "PUBLIC"

# ── AJOUT UTS ──────────────────────────────────────────────
class StatutCircuitEnum(str, Enum):
    EN_COURS   = "EN_COURS"
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REJETE     = "REJETE"
    PUBLIE     = "PUBLIE"

class ActionCircuitEnum(str, Enum):
    ENVOYE   = "ENVOYE"
    RECU     = "RECU"
    MODIFIE  = "MODIFIE"
    REMPLACE = "REMPLACE"
    TRANSMIS = "TRANSMIS"
    VALIDE   = "VALIDE"
    REJETE   = "REJETE"
    RETOURNE = "RETOURNE"
    COMMENTE = "COMMENTE"

# ── Document ───────────────────────────────────────────────
class DocumentCreate(BaseModel):
    titre:          str
    type_ressource: TypeRessourceEnum
    id_module:      Optional[int] = None
    id_filiere:     Optional[int] = None
    id_univ:        Optional[int] = None
    visibilite:     Optional[VisibiliteDocumentEnum] = None  # pertinent seulement si ADMINISTRATIF

class DocumentUpdate(BaseModel):
    titre:          Optional[str] = None
    type_ressource: Optional[TypeRessourceEnum] = None
    id_module:      Optional[int] = None

class DocumentResponse(BaseModel):
    id_doc:           int
    titre:            str
    type_ressource:   TypeRessourceEnum
    chemin_fichier:   str
    nom_fichier:      Optional[str]
    taille_fichier:   Optional[int]
    type_mime:        Optional[str]
    texte_ocr:        Optional[str]
    est_valide:       bool
    statut:           StatutDocumentEnum
    motif_refus:      Optional[str]
    date_soumission:  datetime
    date_publication: Optional[datetime]
    id_module:        Optional[int]
    id_filiere:       Optional[int]
    id_univ:          Optional[int]
    visibilite:       Optional[VisibiliteDocumentEnum] = None
    hash_fichier:     Optional[str] = None  # AJOUT SECURITE UTS — empreinte SHA-256 courante
    auteur_poste_id:  Optional[str] = None  # AJOUT SECURITE UTS — poste propriétaire (via circuit), utilisé pour le cloisonnement en recherche

    class Config:
        from_attributes = True

class DocumentValider(BaseModel):
    statut:      StatutDocumentEnum
    motif_refus: Optional[str] = None

    @field_validator("motif_refus")
    @classmethod
    def motif_requis_si_refuse(cls, v, info):
        if info.data.get("statut") == StatutDocumentEnum.REFUSE and not v:
            raise ValueError("Le motif est obligatoire en cas de refus")
        return v

# ── Planning ───────────────────────────────────────────────
class PlanningCreate(BaseModel):
    semaine:    str
    titre:      str
    id_filiere: Optional[int] = None
    id_univ:    Optional[int] = None

class PlanningResponse(BaseModel):
    id_planning: int
    semaine:     str
    titre:       str
    fichier_url: Optional[str]
    est_publie:  bool
    date_envoi:  datetime
    id_filiere:  Optional[int]
    id_univ:     Optional[int]

    class Config:
        from_attributes = True

# ── Annonce ────────────────────────────────────────────────
class AnnonceCreate(BaseModel):
    titre:           str
    contenu:         str
    date_expiration: Optional[datetime] = None
    id_filiere:      Optional[int] = None
    id_univ:         Optional[int] = None

class AnnonceResponse(BaseModel):
    id_annonce:      int
    titre:           str
    contenu:         str
    date_creation:   datetime
    date_expiration: Optional[datetime]
    est_publiee:     bool
    id_filiere:      Optional[int]
    id_univ:         Optional[int]

    class Config:
        from_attributes = True

# ── Upload fichier ─────────────────────────────────────────
class UploadResponse(BaseModel):
    nom_fichier:    str
    chemin_fichier: str
    taille_fichier: int
    type_mime:      str
    message:        str = "Fichier uploade avec succes"


# ══════════════════════════════════════════════════════════
# AJOUT UTS — Schemas circuit documentaire
# ══════════════════════════════════════════════════════════

class CircuitCreate(BaseModel):
    """
    Créer un nouveau circuit documentaire.
    circuit = liste ordonnée des poste_id destinataires.
    ex: ["ssm", "dsi", "vp-eip", "president"]
    """
    document_id:      int
    circuit:          List[str]          # au moins 1 destinataire
    objet:            Optional[str] = None
    commentaire_init: Optional[str] = None
    # AJOUT SECURITE UTS — Point 3 : delai/echeance de traitement du circuit
    date_limite:      Optional[datetime] = None

    @field_validator("circuit")
    @classmethod
    def circuit_non_vide(cls, v):
        if not v:
            raise ValueError("Le circuit doit contenir au moins un destinataire")
        return v


class HistoriqueResponse(BaseModel):
    id:                   int
    circuit_id:           int
    acteur_poste_id:      Optional[str]
    acteur_nom:           Optional[str]
    action:               ActionCircuitEnum
    niveau_avant:         Optional[int]
    niveau_apres:         Optional[int]
    commentaire:          Optional[str]
    date_action:          datetime
    duree_etape_secondes: Optional[int]
    # AJOUT SECURITE UTS — Point 2 : tracabilite renforcee (validee)
    hash_fichier:         Optional[str] = None
    ip_address:           Optional[str] = None
    user_agent:           Optional[str] = None

    class Config:
        from_attributes = True


class CircuitResponse(BaseModel):
    id:                  int
    document_id:         int
    auteur_poste_id:     Optional[str]
    circuit:             List[Any]        # liste des poste_id
    niveau_index:        int
    statut:              StatutCircuitEnum
    objet:               Optional[str]
    commentaire_init:    Optional[str]
    date_envoi:          datetime
    date_derniere_action: datetime
    date_cloture:        Optional[datetime]
    date_limite:         Optional[datetime] = None
    # AJOUT SECURITE UTS (Point 3) — calculé à la volée, jamais stocké en base :
    # "EN_RETARD" / "A_VENIR" (échéance < 48h) / "DANS_LES_TEMPS" / None (pas d'échéance
    # définie, ou circuit déjà clôturé).
    statut_echeance:     Optional[str] = None
    historique:          List[HistoriqueResponse] = []

    class Config:
        from_attributes = True


class ActionRequest(BaseModel):
    """
    Corps commun pour transmettre / valider / rejeter / retourner / commenter.
    action      : l'action effectuée (TRANSMIS, VALIDE, REJETE, RETOURNE, COMMENTE)
    commentaire : obligatoire pour REJETE et RETOURNE
    etapes_ajout: liste de poste_id à ajouter AVANT transmission (Objectif 1.2)
    """
    action:       ActionCircuitEnum
    commentaire:  Optional[str] = None
    etapes_ajout: Optional[List[str]] = None   # Objectif 1.2 : étendre le circuit

    @field_validator("commentaire")
    @classmethod
    def commentaire_requis(cls, v, info):
        action = info.data.get("action")
        if action in (ActionCircuitEnum.REJETE, ActionCircuitEnum.RETOURNE) and not v:
            raise ValueError("Un commentaire est obligatoire pour REJETE ou RETOURNE")
        return v


class ModifierDocumentRequest(BaseModel):
    """Modifier les métadonnées du document à l'étape courante."""
    titre:          Optional[str] = None
    type_ressource: Optional[TypeRessourceEnum] = None
    id_module:      Optional[int] = None
    id_filiere:     Optional[int] = None
    commentaire:    Optional[str] = None
