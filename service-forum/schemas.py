from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class StatutPostEnum(str, Enum):
    VISIBLE = "VISIBLE"
    MASQUE  = "MASQUE"
    SIGNALE = "SIGNALE"

class CategorieEnum(str, Enum):
    COURS   = "COURS"
    EXAMEN  = "EXAMEN"
    STAGE   = "STAGE"
    VIE_UNI = "VIE_UNI"
    AUTRE   = "AUTRE"

# ── Réponse ────────────────────────────────────────────────
class ReponseCreate(BaseModel):
    contenu:    str
    auteur_nom: Optional[str] = "Anonyme"
    auteur_id:  Optional[str] = None

class ReponseResponse(BaseModel):
    id_reponse:    int
    contenu:       str
    statut:        StatutPostEnum
    est_solution:  bool
    nb_likes:      int
    date_creation: datetime
    date_modif:    Optional[datetime]
    id_sujet:      int
    auteur_nom:    Optional[str]

    class Config:
        from_attributes = True

# ── Sujet ──────────────────────────────────────────────────
class SujetCreate(BaseModel):
    titre:      str
    contenu:    str
    categorie:  CategorieEnum = CategorieEnum.AUTRE
    id_filiere: Optional[int] = None
    id_univ:    Optional[int] = None
    auteur_nom: Optional[str] = "Anonyme"
    auteur_id:  Optional[str] = None

    @field_validator("titre")
    @classmethod
    def titre_non_vide(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Le titre doit faire au moins 5 caracteres")
        return v.strip()

class SujetResponse(BaseModel):
    id_sujet:      int
    titre:         str
    contenu:       str
    categorie:     CategorieEnum
    statut:        StatutPostEnum
    est_epingle:   bool
    est_resolu:    bool
    nb_vues:       int
    date_creation: datetime
    date_modif:    Optional[datetime]
    id_filiere:    Optional[int]
    id_univ:       Optional[int]
    auteur_nom:    Optional[str]
    reponses:      List[ReponseResponse] = []

    class Config:
        from_attributes = True

class SujetResume(BaseModel):
    """Version légère pour les listes (sans les réponses)."""
    id_sujet:      int
    titre:         str
    categorie:     CategorieEnum
    statut:        StatutPostEnum
    est_epingle:   bool
    est_resolu:    bool
    nb_vues:       int
    nb_reponses:   int = 0
    date_creation: datetime
    auteur_nom:    Optional[str]
    id_filiere:    Optional[int]

    class Config:
        from_attributes = True

# ── Modération ─────────────────────────────────────────────
class ModerationAction(BaseModel):
    statut: StatutPostEnum
    raison: Optional[str] = None

class SignalementCreate(BaseModel):
    raison:      str
    id_sujet:    Optional[int] = None
    id_reponse:  Optional[int] = None
    signale_par: Optional[str] = None

class SignalementResponse(BaseModel):
    id_signalement:   int
    raison:           str
    date_signalement: datetime
    traite:           bool
    id_sujet:         Optional[int]
    id_reponse:       Optional[int]

    class Config:
        from_attributes = True

# ── Stats ──────────────────────────────────────────────────
class ForumStats(BaseModel):
    total_sujets:     int
    sujets_resolus:   int
    total_reponses:   int
    total_signalements_non_traites: int