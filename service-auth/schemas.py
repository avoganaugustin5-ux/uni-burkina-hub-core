from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from models import RoleEnum, SexeEnum, TypeIdentiteEnum

# ── Auth ───────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str          # Email ou username (comme dans ta maquette)
    mot_de_passe: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    user_id: UUID
    nom: str
    prenom: str
    redirect_url: str   # URL du dashboard selon le rôle

# ── Inscription (formulaire Création de Compte) ────────────
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
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v

# ── Réponses utilisateur ───────────────────────────────────
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

# ── Mot de passe oublié ────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    nouveau_mot_de_passe: str
    confirm_mot_de_passe: str

# ── Structures académiques ─────────────────────────────────
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
class NotificationResponse(BaseModel):
    id_notif: int
    titre: str
    message: str
    est_lue: bool
    date_envoi: datetime
    class Config:
        from_attributes = True