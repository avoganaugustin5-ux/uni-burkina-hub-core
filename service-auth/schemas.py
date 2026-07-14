from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from models import RoleEnum, SexeEnum, TypeIdentiteEnum

# ── Auth ───────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    mot_de_passe: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    user_id: UUID
    nom: str
    prenom: str
    redirect_url: str

# ── Inscription ────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    nom: str
    prenom: str
    email: EmailStr
    mot_de_passe: str
    confirm_mot_de_passe: str
    sexe: Optional[SexeEnum] = None
    date_naissance: Optional[datetime] = None
    id_univ: Optional[int] = None
    photo_profil_url: Optional[str] = None
    role: RoleEnum = RoleEnum.ETUDIANT
    # ── AJOUT UTS ──────────────────────────────────────────────
    # poste_id/branche/type_poste : remplis automatiquement par le frontend a partir de
    # UTS_ORG (uts_org_data.js) quand role appartient a {VP_EIP,VP_RCU,SG,CABINET,DIRECTEUR,EMPLOYE,PRESIDENT}.
    poste_id:    Optional[str] = None
    branche:     Optional[str] = None
    type_poste:  Optional[str] = None
    # id_ufr_gere : uniquement si role == CHEF_DEPARTEMENT — l'UFR dont la personne est chef.
    id_ufr_gere: Optional[int] = None
    # ── AJOUT UTS — inscription académique (étudiant/délégué) ──
    id_filiere:   Optional[int] = None   # filière choisie lors de l'inscription
    niveau_etude: Optional[str] = None   # L1, L2, L3, M1, M2

    @field_validator("confirm_mot_de_passe")
    @classmethod
    def passwords_match(cls, v, info):
        if "mot_de_passe" in info.data and v != info.data["mot_de_passe"]:
            raise ValueError("Les mots de passe ne correspondent pas")
        return v

    @field_validator("mot_de_passe")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        return v

# ── Reponses utilisateur ───────────────────────────────────
class UserResponse(BaseModel):
    id: UUID
    nom: str
    prenom: str
    email: str
    username: str
    role: RoleEnum
    sexe: Optional[SexeEnum]
    photo_profil_url: Optional[str]
    actif: bool
    date_inscription: datetime
    # ── AJOUT UTS — necessaire pour que service-ged sache QUI agit via /auth/me ──
    poste_id:    Optional[str] = None
    branche:     Optional[str] = None
    type_poste:  Optional[str] = None
    id_ufr_gere: Optional[int] = None
    derniere_connexion: Optional[datetime]
    id_univ: Optional[int]

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    ville_actuelle: Optional[str] = None
    photo_profil_url: Optional[str] = None

# ── AJOUT — Annuaire minimal (choix de destinataire dans un circuit) ──────
# Volontairement restreint : ni email, ni username, ni téléphone — accessible
# à tout utilisateur connecté, contrairement à /utilisateurs (réservé admin).
class AnnuaireEntry(BaseModel):
    id: UUID
    nom: str
    prenom: str
    role: RoleEnum
    poste_id: Optional[str] = None
    branche: Optional[str] = None

    class Config:
        from_attributes = True

# ── Mot de passe oublie ────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    nouveau_mot_de_passe: str
    confirm_mot_de_passe: str

# ── Changement de mot de passe (utilisateur connecte) ──────
class ChangePasswordRequest(BaseModel):
    mot_de_passe_actuel: str
    nouveau_mot_de_passe: str
    confirmer_mot_de_passe: str

    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 8 caracteres")
        return v

    @field_validator("confirmer_mot_de_passe")
    @classmethod
    def passwords_match(cls, v, info):
        if "nouveau_mot_de_passe" in info.data and v != info.data["nouveau_mot_de_passe"]:
            raise ValueError("Les nouveaux mots de passe ne correspondent pas")
        return v

# ── Structures academiques ─────────────────────────────────
class UniversiteCreate(BaseModel):
    nom_univ: str
    localisation: Optional[str] = None

class UniversiteResponse(BaseModel):
    id_univ: int
    nom_univ: str
    localisation: Optional[str]
    actif: bool
    class Config:
        from_attributes = True

class UFRCreate(BaseModel):
    nom_ufr: str
    code_ufr: str
    id_univ: int

class UFRResponse(BaseModel):
    id_ufr: int
    nom_ufr: str
    code_ufr: str
    id_univ: int
    class Config:
        from_attributes = True

class FiliereCreate(BaseModel):
    nom_filiere: str
    description: Optional[str] = None
    id_ufr: int

class FiliereResponse(BaseModel):
    id_filiere: int
    nom_filiere: str
    description: Optional[str]
    id_ufr: int
    class Config:
        from_attributes = True

class ModuleCreate(BaseModel):
    code_module: str
    libelle: str
    coefficient: int = 1
    id_filiere: int

class ModuleResponse(BaseModel):
    id_module: int
    code_module: str
    libelle: str
    coefficient: int
    id_filiere: int
    class Config:
        from_attributes = True

# ── Notification ───────────────────────────────────────────
class NotificationCreate(BaseModel):
    titre:   str
    message: str
    user_id: UUID

class NotificationResponse(BaseModel):
    id_notif: int
    titre: str
    message: str
    est_lue: bool
    date_envoi: datetime
    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — Cloisonnement documentaire par service (Point 4/5)
# ══════════════════════════════════════════════════════════

class PerimetreResponse(BaseModel):
    """
    Perimetre documentaire d'un utilisateur : la liste des poste_id dont il
    peut voir/consulter les documents administratifs, calculee a partir de
    son groupe de service (et, pour un chef de branche, des groupes places
    sous son autorite).
    """
    poste_ids:            list[str]
    groupe_role_code:     Optional[str] = None
    vision_globale:       bool = False
    branches_supervisees: list[str] = []


class VerifierCodeRequest(BaseModel):
    role_code: str   # le groupe_role_code du service proprietaire du document consulte
    code:      str


class VerifierCodeResponse(BaseModel):
    valide:    bool
    role_code: str


class GroupeServiceMembreOut(BaseModel):
    poste_id: str
    label: Optional[str] = None
    branche_supervisee: Optional[str] = None


class GroupeServiceOut(BaseModel):
    id: int
    role_code: str
    label: str
    description: Optional[str] = None
    branche: Optional[str] = None
    couleur: Optional[str] = None
    code_defini: bool
    membres: list[GroupeServiceMembreOut] = []


class GroupeServiceCreate(BaseModel):
    role_code: str
    label: str
    description: Optional[str] = None
    branche: Optional[str] = None
    couleur: Optional[str] = None


class GroupeServiceUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    branche: Optional[str] = None
    couleur: Optional[str] = None


class DefinirCodeRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def code_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Le code de securite doit contenir au moins 6 caracteres")
        return v


class MembresGroupeRequest(BaseModel):
    poste_ids: list[str]
