from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional
import os

from database import get_db
from models import Utilisateur, RoleEnum, JournalAudit, Universite, UFR, Filiere, Module
from schemas import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse,
    UserUpdate, ForgotPasswordRequest, UniversiteCreate, UniversiteResponse,
    UFRCreate, UFRResponse, FiliereCreate, FiliereResponse,
    ModuleCreate, ModuleResponse, NotificationResponse
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "changez_moi")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

DASHBOARD_URLS = {
    RoleEnum.ADMIN:      "/admin/dashboard",
    RoleEnum.PRESIDENT:  "/president/dashboard",
    RoleEnum.SOUS_ADMIN: "/sous-admin/dashboard",
    RoleEnum.ENSEIGNANT: "/enseignant/dashboard",
    RoleEnum.DELEGUE:    "/delegue/dashboard",
    RoleEnum.ETUDIANT:   "/etudiant/dashboard",
}

# ── Helpers ────────────────────────────────────────────────
def creer_token(user: Utilisateur) -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    payload = {
        "sub":    str(user.id),
        "role":   user.role,
        "nom":    user.nom,
        "prenom": user.prenom,
        "exp":    expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def extraire_token(authorization: Optional[str]) -> str:
    """Extrait le token depuis le header Authorization: Bearer <token>"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Token manquant ou format invalide (Bearer <token>)")
    return authorization[7:]  # supprime "Bearer "

def get_user_from_token(token: str, db: Session) -> Utilisateur:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(Utilisateur, payload["sub"])
        if not user or not user.actif:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide")
        return user
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide ou expiré")

def require_admin(user: Utilisateur):
    if user.role != RoleEnum.ADMIN:
        raise HTTPException(403, "Accès réservé à l'administrateur global")

def require_admin_or_sous_admin(user: Utilisateur):
    if user.role not in [RoleEnum.ADMIN, RoleEnum.SOUS_ADMIN]:
        raise HTTPException(403, "Accès réservé aux administrateurs")

def journaliser(db: Session, action: str, description: str,
                user_id=None, ip: str = None):
    log = JournalAudit(action=action, description=description,
                       user_id=user_id, ip_address=ip)
    db.add(log)
    db.commit()

# ══════════════════════════════════════════════════════════
# AUTHENTIFICATION
# ══════════════════════════════════════════════════════════

@router.post("/register", response_model=UserResponse, status_code=201,
             summary="Créer un compte")
def register(data: RegisterRequest, request: Request,
             db: Session = Depends(get_db)):
    if db.query(Utilisateur).filter_by(email=data.email).first():
        raise HTTPException(400, "Cet email est déjà utilisé")
    if db.query(Utilisateur).filter_by(username=data.username).first():
        raise HTTPException(400, "Ce nom d'utilisateur est déjà pris")

    user = Utilisateur(
        nom=data.nom, prenom=data.prenom,
        username=data.username, email=data.email,
        mot_de_passe=pwd_context.hash(data.mot_de_passe),
        sexe=data.sexe, date_naissance=data.date_naissance,
        id_univ=data.id_univ, role=data.role,
        photo_profil_url=data.photo_profil_url,
    )
    db.add(user); db.commit(); db.refresh(user)
    journaliser(db, "REGISTER",
                f"Nouveau compte : {user.email} | Rôle : {user.role}",
                user_id=user.id, ip=request.client.host)
    return user


@router.post("/login", response_model=TokenResponse,
             summary="Connexion")
def login(data: LoginRequest, request: Request,
          db: Session = Depends(get_db)):
    user = (db.query(Utilisateur).filter_by(email=data.email).first() or
            db.query(Utilisateur).filter_by(username=data.email).first())

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants incorrects")
    if user.tentatives_connexion >= 5:
        raise HTTPException(403, "Compte bloqué après 5 tentatives.")
    if not pwd_context.verify(data.mot_de_passe, user.mot_de_passe):
        user.tentatives_connexion += 1
        db.commit()
        restant = 5 - user.tentatives_connexion
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Mot de passe incorrect. {restant} tentative(s) restante(s).")
    if not user.actif:
        raise HTTPException(403, "Compte désactivé.")

    user.tentatives_connexion = 0
    user.derniere_connexion = datetime.utcnow()
    db.commit()
    journaliser(db, "LOGIN",
                f"Connexion : {user.email} | Rôle : {user.role}",
                user_id=user.id, ip=request.client.host)
    return TokenResponse(
        access_token=creer_token(user),
        role=user.role,
        user_id=user.id,
        nom=user.nom,
        prenom=user.prenom,
        redirect_url=DASHBOARD_URLS[user.role]
    )


@router.post("/logout", summary="Déconnexion")
def logout(request: Request,
           authorization: Optional[str] = Header(None),
           db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    journaliser(db, "LOGOUT", f"Déconnexion : {user.email}",
                user_id=user.id, ip=request.client.host)
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=UserResponse, summary="Mon profil")
def get_me(authorization: Optional[str] = Header(None),
           db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    return get_user_from_token(token, db)


@router.put("/me", response_model=UserResponse, summary="Modifier mon profil")
def update_me(data: UserUpdate,
              authorization: Optional[str] = Header(None),
              db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit(); db.refresh(user)
    return user


@router.post("/mot-de-passe-oublie", summary="Mot de passe oublié")
def forgot_password(data: ForgotPasswordRequest,
                    db: Session = Depends(get_db)):
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


# ══════════════════════════════════════════════════════════
# GESTION UTILISATEURS
# ══════════════════════════════════════════════════════════

@router.get("/utilisateurs", response_model=list[UserResponse],
            summary="Liste tous les utilisateurs")
def list_users(authorization: Optional[str] = Header(None),
               db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    require_admin_or_sous_admin(user)
    return db.query(Utilisateur).all()


@router.get("/utilisateurs/{user_id}", response_model=UserResponse)
def get_user(user_id: str,
             authorization: Optional[str] = Header(None),
             db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    get_user_from_token(token, db)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    return user


@router.delete("/utilisateurs/{user_id}", summary="Désactiver un utilisateur")
def deactivate_user(user_id: str,
                    authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin(admin)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    user.actif = False
    db.commit()
    journaliser(db, "DEACTIVATE_USER",
                f"Désactivation de {user.email}", user_id=admin.id)
    return {"message": f"Compte de {user.nom} {user.prenom} désactivé"}


# ══════════════════════════════════════════════════════════
# ARBORESCENCE
# ══════════════════════════════════════════════════════════

@router.get("/universites", response_model=list[UniversiteResponse])
def list_universites(db: Session = Depends(get_db)):
    return db.query(Universite).filter_by(actif=True).all()


@router.post("/universites", response_model=UniversiteResponse, status_code=201)
def create_universite(data: UniversiteCreate,
                      authorization: Optional[str] = Header(None),
                      db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin(admin)
    univ = Universite(**data.model_dump())
    db.add(univ); db.commit(); db.refresh(univ)
    return univ


@router.get("/ufrs", response_model=list[UFRResponse])
def list_ufrs(db: Session = Depends(get_db)):
    return db.query(UFR).all()


@router.post("/ufrs", response_model=UFRResponse, status_code=201)
def create_ufr(data: UFRCreate,
               authorization: Optional[str] = Header(None),
               db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    ufr = UFR(**data.model_dump())
    db.add(ufr); db.commit(); db.refresh(ufr)
    return ufr


@router.get("/filieres", response_model=list[FiliereResponse])
def list_filieres(db: Session = Depends(get_db)):
    return db.query(Filiere).all()


@router.post("/filieres", response_model=FiliereResponse, status_code=201)
def create_filiere(data: FiliereCreate,
                   authorization: Optional[str] = Header(None),
                   db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    filiere = Filiere(**data.model_dump())
    db.add(filiere); db.commit(); db.refresh(filiere)
    return filiere


@router.get("/modules", response_model=list[ModuleResponse])
def list_modules(db: Session = Depends(get_db)):
    return db.query(Module).all()


@router.post("/modules", response_model=ModuleResponse, status_code=201)
def create_module(data: ModuleCreate,
                  authorization: Optional[str] = Header(None),
                  db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    module = Module(**data.model_dump())
    db.add(module); db.commit(); db.refresh(module)
    return module


# ══════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════

@router.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(authorization: Optional[str] = Header(None),
                      db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    return user.notifications


@router.put("/notifications/{notif_id}/lue")
def mark_notif_read(notif_id: int,
                    authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    from models import Notification
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    notif = db.query(Notification).filter_by(
        id_notif=notif_id, user_id=user.id).first()
    if not notif:
        raise HTTPException(404, "Notification introuvable")
    notif.est_lue = True
    db.commit()
    return {"message": "Notification marquée comme lue"}