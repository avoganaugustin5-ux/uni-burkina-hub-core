from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

# ── Enums ──────────────────────────────────────────────────
class TypeRessourceEnum(str, Enum):
    COURS   = "COURS"
    TD      = "TD"
    EXAMEN  = "EXAMEN"
    ARCHIVE = "ARCHIVE"

class StatutDocumentEnum(str, Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REFUSE     = "REFUSE"

# ── Document ───────────────────────────────────────────────
class DocumentCreate(BaseModel):
    titre:          str
    type_ressource: TypeRessourceEnum
    id_module:      Optional[int] = None
    id_filiere:     Optional[int] = None
    id_univ:        Optional[int] = None

class DocumentUpdate(BaseModel):
    titre:          Optional[str] = None
    type_ressource: Optional[TypeRessourceEnum] = None
    id_module:      Optional[int] = None

class DocumentResponse(BaseModel):
    id_doc:          int
    titre:           str
    type_ressource:  TypeRessourceEnum
    chemin_fichier:  str
    nom_fichier:     Optional[str]
    taille_fichier:  Optional[int]
    type_mime:       Optional[str]
    texte_ocr:       Optional[str]
    est_valide:      bool
    statut:          StatutDocumentEnum
    motif_refus:     Optional[str]
    date_soumission: datetime
    date_publication: Optional[datetime]
    id_module:       Optional[int]
    id_filiere:      Optional[int]
    id_univ:         Optional[int]

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