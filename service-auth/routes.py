from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional
import os, secrets, string, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import get_db
from models import (
    Utilisateur, RoleEnum, JournalAudit, Universite, UFR, Filiere, Module,
    GroupeService, GroupeServiceMembre,
)
from schemas import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse,
    UserUpdate, ForgotPasswordRequest, ChangePasswordRequest,
    UniversiteCreate, UniversiteResponse,
    UFRCreate, UFRResponse, FiliereCreate, FiliereResponse,
    ModuleCreate, ModuleResponse, NotificationResponse, NotificationCreate,
    AnnuaireEntry,
    PerimetreResponse, VerifierCodeRequest, VerifierCodeResponse,
    GroupeServiceOut, GroupeServiceMembreOut, GroupeServiceCreate,
    GroupeServiceUpdate, DefinirCodeRequest, MembresGroupeRequest,
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "changez_moi")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

# ── Config email (a definir dans service-auth/.env) ────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM",     "UniBurkina Hub <noreply@uniburkina.bf>")

DASHBOARD_URLS = {
    RoleEnum.ADMIN:      "/admin/dashboard",
    RoleEnum.PRESIDENT:  "/president/dashboard",
    RoleEnum.SOUS_ADMIN: "/sous-admin/dashboard",
    RoleEnum.ENSEIGNANT: "/enseignant/dashboard",
    RoleEnum.DELEGUE:    "/delegue/dashboard",
    RoleEnum.ETUDIANT:   "/etudiant/dashboard",
    # ── AJOUT UTS — sans ces entrees, login() leve une KeyError pour ces roles ──
    RoleEnum.CHEF_DEPARTEMENT: "/chef-dept/dashboard",
    RoleEnum.VP_EIP:           "/vp/dashboard",
    RoleEnum.VP_RCU:           "/vp/dashboard",
    RoleEnum.SG:               "/sg/dashboard",
    RoleEnum.CABINET:          "/cabinet/dashboard",
    RoleEnum.DIRECTEUR:        "/directeur/dashboard",
    RoleEnum.EMPLOYE:          "/employe/dashboard",
}

# ── AJOUT UTS — roles "Direction" qui necessitent une validation manuelle du Super-Admin ──
# (cf. uts_register_extended.html : "Votre compte Direction sera active apres validation")
# On reutilise volontairement la colonne 'actif' existante (False = en attente de validation),
# le login() ci-dessous bloque deja les comptes actif=False, donc aucune autre modification
# n'est necessaire pour empecher la connexion avant validation.
ROLES_VALIDATION_MANUELLE = set()  # MODIFIE UTS — tous actifs immediatement

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Token manquant ou format invalide (Bearer <token>)")
    return authorization[7:]

def get_user_from_token(token: str, db: Session) -> Utilisateur:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(Utilisateur, payload["sub"])
        if not user or not user.actif:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide")
        return user
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide ou expire")

def require_admin(user: Utilisateur):
    if user.role != RoleEnum.ADMIN:
        raise HTTPException(403, "Acces reserve a l'administrateur global")

def require_admin_or_sous_admin(user: Utilisateur):
    if user.role not in [RoleEnum.ADMIN, RoleEnum.SOUS_ADMIN]:
        raise HTTPException(403, "Acces reserve aux administrateurs")

def journaliser(db: Session, action: str, description: str,
                user_id=None, ip: str = None):
    log = JournalAudit(action=action, description=description,
                       user_id=user_id, ip_address=ip)
    db.add(log)
    db.commit()

def generer_mot_de_passe(longueur: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    mdp = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    mdp += [secrets.choice(alphabet) for _ in range(longueur - 3)]
    secrets.SystemRandom().shuffle(mdp)
    return "".join(mdp)

def envoyer_email_reset(destinataire: str, prenom: str, nom: str, nouveau_mdp: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    role_labels = {}
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Reinitialisation de mot de passe</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- EN-TETE -->
        <tr>
          <td style="background:#0f1e1a;border-radius:14px 14px 0 0;padding:32px 40px;text-align:center;">
            <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>
                <td style="background:#1D9E75;border-radius:10px;width:48px;height:48px;text-align:center;vertical-align:middle;">
                  <span style="color:#fff;font-size:22px;font-weight:800;font-family:Georgia,serif;">UB</span>
                </td>
                <td style="padding-left:12px;text-align:left;">
                  <div style="color:#fff;font-size:18px;font-weight:700;font-family:Georgia,serif;">UniBurkina <span style="color:#1D9E75;">Hub</span></div>
                  <div style="color:#8aa39b;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Plateforme Universitaire UTS</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- BANDE VERTE -->
        <tr>
          <td style="background:#1D9E75;height:4px;"></td>
        </tr>

        <!-- CORPS -->
        <tr>
          <td style="background:#ffffff;padding:40px 40px 32px;border-left:1px solid #dde8e4;border-right:1px solid #dde8e4;">

            <!-- Icone cadenas -->
            <table cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
              <tr>
                <td style="background:#E8F7F2;border-radius:50%;width:64px;height:64px;text-align:center;vertical-align:middle;">
                  <span style="font-size:32px;">&#128274;</span>
                </td>
              </tr>
            </table>

            <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#12221d;text-align:center;">
              Reinitialisation de mot de passe
            </h1>
            <p style="margin:0 0 24px;font-size:14px;color:#4d6b61;text-align:center;">
              Bonjour <strong>{prenom} {nom}</strong>, voici votre nouveau mot de passe temporaire.
            </p>

            <!-- Encart mot de passe -->
            <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
              <tr>
                <td style="background:#f4f6f5;border:2px dashed #1D9E75;border-radius:12px;padding:20px;text-align:center;">
                  <div style="font-size:11px;font-weight:700;color:#8aa39b;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">
                    Votre nouveau mot de passe temporaire
                  </div>
                  <div style="font-family:'Courier New',monospace;font-size:24px;font-weight:700;color:#1D9E75;letter-spacing:4px;background:#fff;border:1px solid #dde8e4;border-radius:8px;padding:12px 20px;display:inline-block;">
                    {nouveau_mdp}
                  </div>
                </td>
              </tr>
            </table>

            <!-- Etapes -->
            <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:28px;">
              <tr>
                <td style="background:#E8F7F2;border-radius:10px;padding:20px 24px;">
                  <div style="font-size:13px;font-weight:700;color:#137a58;margin-bottom:12px;">
                    &#9654; Etapes a suivre
                  </div>
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="vertical-align:top;padding-right:10px;">
                        <div style="background:#1D9E75;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;font-size:11px;font-weight:700;line-height:22px;">1</div>
                      </td>
                      <td style="font-size:13px;color:#12221d;padding-bottom:10px;">
                        Connectez-vous sur <a href="http://localhost:8000/connexion" style="color:#1D9E75;font-weight:600;">UniBurkina Hub</a> avec ce mot de passe temporaire.
                      </td>
                    </tr>
                    <tr>
                      <td style="vertical-align:top;padding-right:10px;">
                        <div style="background:#1D9E75;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;font-size:11px;font-weight:700;line-height:22px;">2</div>
                      </td>
                      <td style="font-size:13px;color:#12221d;padding-bottom:10px;">
                        Rendez-vous dans <strong>Mon profil &rarr; Securite</strong> pour definir un nouveau mot de passe personnel.
                      </td>
                    </tr>
                    <tr>
                      <td style="vertical-align:top;padding-right:10px;">
                        <div style="background:#1D9E75;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;font-size:11px;font-weight:700;line-height:22px;">3</div>
                      </td>
                      <td style="font-size:13px;color:#12221d;">
                        Ne partagez jamais ce mot de passe avec quiconque.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- Bouton connexion -->
            <table cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
              <tr>
                <td style="background:#1D9E75;border-radius:9px;padding:13px 32px;text-align:center;">
                  <a href="http://localhost:8000/connexion" style="color:#fff;font-size:14px;font-weight:700;text-decoration:none;letter-spacing:0.3px;">
                    Se connecter maintenant &rarr;
                  </a>
                </td>
              </tr>
            </table>

            <!-- Avertissement -->
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="background:#FFF8E1;border:1px solid #F0D98B;border-radius:8px;padding:14px 18px;">
                  <p style="margin:0;font-size:12px;color:#7a5c00;">
                    <strong>&#9888; Important :</strong> Si vous n'avez pas demande cette reinitialisation, contactez immediatement l'administrateur de la plateforme.
                  </p>
                </td>
              </tr>
            </table>

          </td>
        </tr>

        <!-- PIED DE PAGE -->
        <tr>
          <td style="background:#f4f6f5;border:1px solid #dde8e4;border-top:none;border-radius:0 0 14px 14px;padding:24px 40px;text-align:center;">
            <p style="margin:0 0 4px;font-size:12px;color:#8aa39b;">
              Cet email a ete envoye automatiquement par <strong style="color:#4d6b61;">UniBurkina Hub</strong>.
            </p>
            <p style="margin:0;font-size:11px;color:#b8cfc9;">
              Universite Thomas SANKARA &mdash; UTS Burkina Faso &mdash; 2025-2026
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    texte_brut = f"""UniBurkina Hub — Reinitialisation de mot de passe

Bonjour {prenom} {nom},

Votre nouveau mot de passe temporaire est : {nouveau_mdp}

Etapes :
1. Connectez-vous sur http://localhost:8000/connexion avec ce mot de passe.
2. Rendez-vous dans Mon profil > Securite pour changer votre mot de passe.
3. Ne partagez jamais ce mot de passe.

Si vous n'avez pas effectue cette demande, contactez l'administrateur.

-- UniBurkina Hub | UTS Burkina Faso 2025-2026"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "UniBurkina Hub — Reinitialisation de votre mot de passe"
        msg["From"]    = SMTP_FROM
        msg["To"]      = destinataire
        msg.attach(MIMEText(texte_brut, "plain", "utf-8"))
        msg.attach(MIMEText(html,       "html",  "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [destinataire], msg.as_string())
        return True
    except Exception as e:
        import logging
        logging.getLogger("service-auth").error(f"Erreur envoi email: {e}")
        return False


def envoyer_email_confirmation_changement(destinataire: str, prenom: str, nom: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Mot de passe modifie</title></head>
<body style="margin:0;padding:0;background:#f4f6f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr>
          <td style="background:#0f1e1a;border-radius:14px 14px 0 0;padding:32px 40px;text-align:center;">
            <span style="color:#fff;font-size:20px;font-weight:700;font-family:Georgia,serif;">
              Uni<span style="color:#1D9E75;">Burkina</span> Hub
            </span>
          </td>
        </tr>
        <tr><td style="background:#1D9E75;height:4px;"></td></tr>
        <tr>
          <td style="background:#fff;padding:40px;border:1px solid #dde8e4;text-align:center;">
            <div style="background:#E8F7F2;border-radius:50%;width:64px;height:64px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;font-size:32px;">&#10003;</div>
            <h1 style="color:#12221d;font-size:20px;margin:0 0 12px;">Mot de passe modifie avec succes</h1>
            <p style="color:#4d6b61;font-size:14px;margin:0 0 24px;">
              Bonjour <strong>{prenom} {nom}</strong>,<br>
              votre mot de passe a ete mis a jour le {datetime.utcnow().strftime("%d/%m/%Y a %Hh%M")} UTC.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
              <tr>
                <td style="background:#FFF8E1;border:1px solid #F0D98B;border-radius:8px;padding:14px 18px;">
                  <p style="margin:0;font-size:12px;color:#7a5c00;">
                    <strong>&#9888;</strong> Si vous n'etes pas a l'origine de cette modification, contactez immediatement l'administrateur.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f4f6f5;border:1px solid #dde8e4;border-top:none;border-radius:0 0 14px 14px;padding:20px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#8aa39b;">UniBurkina Hub &mdash; UTS Burkina Faso &mdash; 2025-2026</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "UniBurkina Hub — Votre mot de passe a ete modifie"
        msg["From"]    = SMTP_FROM
        msg["To"]      = destinataire
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo(); server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [destinataire], msg.as_string())
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════
# AUTHENTIFICATION
# ══════════════════════════════════════════════════════════

@router.post("/register", response_model=UserResponse, status_code=201,
             summary="Creer un compte")
def register(data: RegisterRequest, request: Request,
             db: Session = Depends(get_db)):
    if db.query(Utilisateur).filter_by(email=data.email).first():
        raise HTTPException(400, "Cet email est deja utilise")
    if db.query(Utilisateur).filter_by(username=data.username).first():
        raise HTTPException(400, "Ce nom d'utilisateur est deja pris")

    # ── AJOUT UTS — les comptes Direction restent inactifs jusqu'a validation du Super-Admin ──
    actif_initial = data.role not in ROLES_VALIDATION_MANUELLE

    user = Utilisateur(
        nom=data.nom, prenom=data.prenom,
        username=data.username, email=data.email,
        mot_de_passe=pwd_context.hash(data.mot_de_passe),
        sexe=data.sexe, date_naissance=data.date_naissance,
        id_univ=data.id_univ, role=data.role,
        photo_profil_url=data.photo_profil_url,
        poste_id=data.poste_id, branche=data.branche,
        type_poste=data.type_poste, id_ufr_gere=data.id_ufr_gere,
        actif=actif_initial,
    )
    db.add(user); db.commit(); db.refresh(user)

    # ── AJOUT UTS — Créer l'inscription académique pour les étudiants ──
    if data.role in (RoleEnum.ETUDIANT, RoleEnum.DELEGUE) and data.id_filiere:
        from models import InscriptionEtudiant
        from datetime import datetime
        inscription = InscriptionEtudiant(
            annee_academique="2025-2026",
            niveau_etude=data.niveau_etude or "L1",
            statut=True,
            etudiant_id=user.id,
            id_filiere=data.id_filiere,
            id_univ=data.id_univ,
        )
        db.add(inscription)
        db.commit()

    journaliser(db, "REGISTER",
                f"Nouveau compte : {user.email} | Role : {user.role} | "
                f"Poste : {user.poste_id or '-'} | Actif : {user.actif}",
                user_id=user.id, ip=request.client.host)
    return user


@router.put("/utilisateurs/{user_id}/activer",
            summary="Activer un compte Direction (reserve au Super-Administrateur)")
def activer_utilisateur(user_id: str, request: Request,
                        authorization: Optional[str] = Header(None),
                        db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin(admin)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    user.actif = True
    db.commit()
    journaliser(db, "ACTIVATE_USER",
                f"Activation du compte Direction de {user.email} par {admin.email}",
                user_id=admin.id, ip=request.client.host)
    return {"message": f"Compte de {user.prenom} {user.nom} active avec succes."}


@router.post("/login", response_model=TokenResponse, summary="Connexion")
def login(data: LoginRequest, request: Request,
          db: Session = Depends(get_db)):
    user = (db.query(Utilisateur).filter_by(email=data.email).first() or
            db.query(Utilisateur).filter_by(username=data.email).first())
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants incorrects")
    if user.tentatives_connexion >= 5:
        raise HTTPException(403, "Compte bloque apres 5 tentatives.")
    if not pwd_context.verify(data.mot_de_passe, user.mot_de_passe):
        user.tentatives_connexion += 1; db.commit()
        restant = 5 - user.tentatives_connexion
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Mot de passe incorrect. {restant} tentative(s) restante(s).")
    if not user.actif:
        raise HTTPException(403, "Compte desactive.")
    user.tentatives_connexion = 0
    user.derniere_connexion = datetime.utcnow()
    db.commit()
    journaliser(db, "LOGIN", f"Connexion : {user.email} | Role : {user.role}",
                user_id=user.id, ip=request.client.host)
    return TokenResponse(
        access_token=creer_token(user), role=user.role,
        user_id=user.id, nom=user.nom, prenom=user.prenom,
        redirect_url=DASHBOARD_URLS[user.role]
    )


@router.post("/logout", summary="Deconnexion")
def logout(request: Request, authorization: Optional[str] = Header(None),
           db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    journaliser(db, "LOGOUT", f"Deconnexion : {user.email}",
                user_id=user.id, ip=request.client.host)
    return {"message": "Deconnexion reussie"}


@router.get("/me", response_model=UserResponse, summary="Mon profil")
def get_me(authorization: Optional[str] = Header(None),
           db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    return get_user_from_token(token, db)


@router.put("/me", response_model=UserResponse, summary="Modifier mon profil")
def update_me(data: UserUpdate, authorization: Optional[str] = Header(None),
              db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit(); db.refresh(user)
    return user


# ══════════════════════════════════════════════════════════
# MOT DE PASSE — Reset + Changement personnel
# ══════════════════════════════════════════════════════════

@router.post("/mot-de-passe-oublie", summary="Mot de passe oublie — envoie un MDP temporaire par email")
def forgot_password(data: ForgotPasswordRequest, request: Request,
                    db: Session = Depends(get_db)):
    # Toujours repondre 200 pour ne pas reveler si l'email existe
    user = db.query(Utilisateur).filter_by(email=data.email).first()
    if not user or not user.actif:
        return {"message": "Si cet email existe, un nouveau mot de passe a ete envoye."}

    nouveau_mdp = generer_mot_de_passe(12)
    user.mot_de_passe = pwd_context.hash(nouveau_mdp)
    user.tentatives_connexion = 0
    db.commit()

    email_ok = envoyer_email_reset(user.email, user.prenom, user.nom, nouveau_mdp)

    journaliser(db, "RESET_PASSWORD",
                f"Reinitialisation MDP pour {user.email} — email_envoye={email_ok}",
                user_id=user.id, ip=request.client.host)

    if not email_ok:
        # SMTP non configure : retourner le mdp en dev (A SUPPRIMER EN PRODUCTION)
        return {
            "message": "Email non configure. En mode developpement, voici le mot de passe temporaire.",
            "dev_password": nouveau_mdp
        }

    return {"message": "Un nouveau mot de passe a ete envoye a votre adresse email."}


@router.put("/me/password", summary="Changer son propre mot de passe")
def change_password(data: "ChangePasswordRequest",
                    authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)

    if not pwd_context.verify(data.mot_de_passe_actuel, user.mot_de_passe):
        raise HTTPException(400, "Mot de passe actuel incorrect.")
    if data.nouveau_mot_de_passe != data.confirmer_mot_de_passe:
        raise HTTPException(400, "Les nouveaux mots de passe ne correspondent pas.")
    if len(data.nouveau_mot_de_passe) < 8:
        raise HTTPException(400, "Le nouveau mot de passe doit contenir au moins 8 caracteres.")
    if pwd_context.verify(data.nouveau_mot_de_passe, user.mot_de_passe):
        raise HTTPException(400, "Le nouveau mot de passe doit etre different de l'ancien.")

    user.mot_de_passe = pwd_context.hash(data.nouveau_mot_de_passe)
    db.commit()

    envoyer_email_confirmation_changement(user.email, user.prenom, user.nom)
    journaliser(db, "CHANGE_PASSWORD",
                f"Changement MDP par {user.email}", user_id=user.id)

    return {"message": "Mot de passe mis a jour avec succes."}


# ══════════════════════════════════════════════════════════
# GESTION UTILISATEURS
# ══════════════════════════════════════════════════════════

@router.get("/utilisateurs", response_model=list[UserResponse])
def list_users(authorization: Optional[str] = Header(None),
               db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    require_admin_or_sous_admin(user)
    return db.query(Utilisateur).all()


@router.get("/annuaire", response_model=list[AnnuaireEntry],
            summary="Liste minimale des comptes occupant un poste (choix de destinataire de circuit)")
def annuaire(authorization: Optional[str] = Header(None),
            db: Session = Depends(get_db)):
    """
    Accessible à TOUT utilisateur authentifié (contrairement à /utilisateurs, admin-only).
    Volontairement limité : uniquement les comptes actifs avec un poste_id renseigné,
    et seulement les champs nom/prenom/role/poste_id/branche — rien de sensible.
    """
    token = extraire_token(authorization)
    get_user_from_token(token, db)  # authentification requise, aucune restriction de role
    return (
        db.query(Utilisateur)
        .filter(Utilisateur.actif == True, Utilisateur.poste_id.isnot(None))  # noqa: E712
        .all()
    )


@router.get("/utilisateurs/{user_id}", response_model=UserResponse)
def get_user(user_id: str, authorization: Optional[str] = Header(None),
             db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    get_user_from_token(token, db)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    return user


@router.get("/utilisateurs-meme-poste/{user_id}",
            summary="Lister les IDs des collègues occupant le même poste (ou à défaut la même branche+rôle)")
def utilisateurs_meme_poste(user_id: str, authorization: Optional[str] = Header(None),
                            db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    get_user_from_token(token, db)  # authentification requise, pas de restriction de role

    ref = db.get(Utilisateur, user_id)
    if not ref:
        raise HTTPException(404, "Utilisateur introuvable")

    q = db.query(Utilisateur).filter(Utilisateur.actif == True)  # noqa: E712
    if ref.poste_id:
        q = q.filter(Utilisateur.poste_id == ref.poste_id)
    elif ref.branche:
        # Repli si poste_id n'est pas renseigné : même branche + même rôle
        q = q.filter(Utilisateur.branche == ref.branche, Utilisateur.role == ref.role)
    else:
        # Dernier repli : même rôle uniquement
        q = q.filter(Utilisateur.role == ref.role)

    collegues = q.all()
    ids = [str(u.id) for u in collegues]
    return {"ids": ids, "total": len(ids)}


@router.delete("/utilisateurs/{user_id}", summary="Desactiver un utilisateur")
def deactivate_user(user_id: str, authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin(admin)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    user.actif = False; db.commit()
    journaliser(db, "DEACTIVATE_USER",
                f"Desactivation de {user.email}", user_id=admin.id)
    return {"message": f"Compte de {user.nom} {user.prenom} desactive"}


@router.delete("/utilisateurs/{user_id}/supprimer", summary="Supprimer définitivement un utilisateur")
def supprimer_utilisateur(user_id: str, authorization: Optional[str] = Header(None),
                          db: Session = Depends(get_db)):
    """Suppression physique irréversible — réservée à l'ADMIN."""
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin(admin)
    user = db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    if str(user.id) == str(admin.id):
        raise HTTPException(400, "Vous ne pouvez pas supprimer votre propre compte")
    email_log = user.email
    # Nullifier les FK dans journal_audit avant suppression (contrainte d'intégrité)
    db.query(JournalAudit).filter(JournalAudit.user_id == user.id).update(
        {"user_id": None}, synchronize_session=False
    )
    db.delete(user)
    db.commit()
    journaliser(db, "DELETE_USER",
                f"Suppression definitive de {email_log}", user_id=admin.id)
    return {"message": "Compte supprimé définitivement"}


# ══════════════════════════════════════════════════════════
# ARBORESCENCE
# ══════════════════════════════════════════════════════════

@router.get("/universites", response_model=list[UniversiteResponse])
def list_universites(db: Session = Depends(get_db)):
    return db.query(Universite).filter_by(actif=True).all()

@router.post("/universites", response_model=UniversiteResponse, status_code=201)
def create_universite(data: UniversiteCreate, authorization: Optional[str] = Header(None),
                      db: Session = Depends(get_db)):
    token = extraire_token(authorization); admin = get_user_from_token(token, db)
    require_admin(admin)
    univ = Universite(**data.model_dump()); db.add(univ); db.commit(); db.refresh(univ)
    return univ

@router.get("/ufrs", response_model=list[UFRResponse])
def list_ufrs(db: Session = Depends(get_db)):
    return db.query(UFR).all()

@router.post("/ufrs", response_model=UFRResponse, status_code=201)
def create_ufr(data: UFRCreate, authorization: Optional[str] = Header(None),
               db: Session = Depends(get_db)):
    token = extraire_token(authorization); admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    ufr = UFR(**data.model_dump()); db.add(ufr); db.commit(); db.refresh(ufr)
    return ufr

@router.get("/filieres", response_model=list[FiliereResponse])
def list_filieres(db: Session = Depends(get_db)):
    return db.query(Filiere).all()

@router.post("/filieres", response_model=FiliereResponse, status_code=201)
def create_filiere(data: FiliereCreate, authorization: Optional[str] = Header(None),
                   db: Session = Depends(get_db)):
    token = extraire_token(authorization); admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    filiere = Filiere(**data.model_dump()); db.add(filiere); db.commit(); db.refresh(filiere)
    return filiere

@router.get("/modules", response_model=list[ModuleResponse])
def list_modules(db: Session = Depends(get_db)):
    return db.query(Module).all()

@router.post("/modules", response_model=ModuleResponse, status_code=201)
def create_module(data: ModuleCreate, authorization: Optional[str] = Header(None),
                  db: Session = Depends(get_db)):
    token = extraire_token(authorization); admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    module = Module(**data.model_dump()); db.add(module); db.commit(); db.refresh(module)
    return module


# ══════════════════════════════════════════════════════════
# AJOUT UTS — Routage automatique etudiant -> chef de departement (Objectif 1.1)
# ══════════════════════════════════════════════════════════

@router.get("/chef-dept-de-etudiant/{user_id}",
            summary="Trouve le chef de departement de l'UFR de cet etudiant, pour le routage automatique")
def chef_dept_de_etudiant(user_id: str, db: Session = Depends(get_db)):
    from models import InscriptionEtudiant, Filiere

    inscription = (
        db.query(InscriptionEtudiant)
        .filter_by(etudiant_id=user_id)
        .order_by(InscriptionEtudiant.id_inscription.desc())
        .first()
    )
    if not inscription:
        raise HTTPException(404, "Aucune inscription trouvee pour cet etudiant — UFR inconnue")

    filiere = db.get(Filiere, inscription.id_filiere)
    if not filiere:
        raise HTTPException(404, "Filiere introuvable pour cette inscription")

    chef = (
        db.query(Utilisateur)
        .filter_by(role=RoleEnum.CHEF_DEPARTEMENT, id_ufr_gere=filiere.id_ufr, actif=True)
        .first()
    )
    if not chef:
        raise HTTPException(
            404,
            "Aucun chef de departement actif n'est assigne a l'UFR de cet etudiant pour le moment."
        )
    return {
        "user_id": str(chef.id),
        "nom": chef.nom,
        "prenom": chef.prenom,
        "id_ufr": filiere.id_ufr,
    }


# ══════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════

@router.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(authorization: Optional[str] = Header(None),
                      db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    return user.notifications

@router.post("/notifications", response_model=NotificationResponse, status_code=201,
             summary="Créer une notification pour un utilisateur (appelé par les autres services)")
def creer_notification(data: NotificationCreate,
                       authorization: Optional[str] = Header(None),
                       db: Session = Depends(get_db)):
    from models import Notification
    # Authentification requise (n'importe quel appelant valide, ex: service-ged/service-ocr
    # relayant le token de l'utilisateur qui a declenche l'action) — pas de restriction de role,
    # le destinataire est précisé dans le corps via user_id.
    token = extraire_token(authorization)
    get_user_from_token(token, db)

    destinataire = db.get(Utilisateur, data.user_id)
    if not destinataire:
        raise HTTPException(404, "Utilisateur destinataire introuvable")

    notif = Notification(
        titre=data.titre,
        message=data.message,
        user_id=data.user_id,
    )
    db.add(notif); db.commit(); db.refresh(notif)
    return notif

@router.put("/notifications/{notif_id}/lue")
def mark_notif_read(notif_id: int, authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    from models import Notification
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    notif = db.query(Notification).filter_by(id_notif=notif_id, user_id=user.id).first()
    if not notif:
        raise HTTPException(404, "Notification introuvable")
    notif.est_lue = True; db.commit()
    return {"message": "Notification marquee comme lue"}


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — Cloisonnement documentaire par service (Point 4)
# + Code de securite partage (Point 5)
# ══════════════════════════════════════════════════════════
#
# Regles validees avec le porteur du projet :
#  - le "service" = un groupe de service (ex: EMPLOYE_DSI = dsi+seap+srss+ssm),
#    pas un poste_id individuel ;
#  - un chef de branche (vp-eip, vp-rcu, sg) voit EN PLUS tous les groupes
#    de sa branche (vision globale) ;
#  - le Chef de Cabinet (ccab) est deja dans le groupe CABINET, qui contient
#    a plat tout le Cabinet (PRCP + ses 3 services inclus) ;
#  - un code de securite est defini par groupe (hash bcrypt, jamais en clair),
#    fixe et modifiable manuellement par un administrateur.

def get_perimetre_utilisateur(db: Session, user: Utilisateur) -> dict:
    """
    Calcule le perimetre documentaire d'un utilisateur : l'ensemble des poste_id
    dont il peut voir/consulter les documents administratifs.
    """
    if not user.poste_id:
        return {
            "poste_ids": [], "groupe_role_code": None,
            "vision_globale": False, "branches_supervisees": [],
        }

    membre = db.query(GroupeServiceMembre).filter_by(poste_id=user.poste_id).first()
    if not membre:
        # Poste renseigne mais pas encore rattache a un groupe de service
        # (organigramme incomplet cote seed) -> perimetre reduit a soi-meme.
        return {
            "poste_ids": [user.poste_id], "groupe_role_code": None,
            "vision_globale": False, "branches_supervisees": [],
        }

    poste_ids = {m.poste_id for m in membre.groupe.membres}
    branches_supervisees = []

    if membre.branche_supervisee:
        branches_supervisees.append(membre.branche_supervisee)
        autres_groupes = (
            db.query(GroupeService)
            .filter(GroupeService.branche == membre.branche_supervisee)
            .all()
        )
        for g in autres_groupes:
            poste_ids.update(m.poste_id for m in g.membres)

    return {
        "poste_ids": sorted(poste_ids),
        "groupe_role_code": membre.groupe.role_code,
        "vision_globale": bool(membre.branche_supervisee),
        "branches_supervisees": branches_supervisees,
    }


@router.get("/groupe-de-poste/{poste_id}",
            summary="Retrouve le role_code du groupe de service d'un poste_id donne (info non sensible)")
def groupe_de_poste(poste_id: str, authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    """
    Utilise par service-ged pour savoir quel code de securite exiger pour un
    document donne (le role_code n'est pas une information sensible en soi,
    contrairement au code lui-meme qui reste hache).
    """
    token = extraire_token(authorization)
    get_user_from_token(token, db)  # authentification requise, aucune restriction de role

    membre = db.query(GroupeServiceMembre).filter_by(poste_id=poste_id).first()
    if not membre:
        return {"poste_id": poste_id, "role_code": None}
    return {"poste_id": poste_id, "role_code": membre.groupe.role_code}


@router.get("/mon-perimetre", response_model=PerimetreResponse,
            summary="Perimetre documentaire de l'utilisateur connecte (cloisonnement par service)")
def mon_perimetre(authorization: Optional[str] = Header(None),
                  db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    return get_perimetre_utilisateur(db, user)


@router.post("/verifier-code-acces", response_model=VerifierCodeResponse,
             summary="Verifie le code de securite partage d'un groupe de service")
def verifier_code_acces(data: VerifierCodeRequest,
                        authorization: Optional[str] = Header(None),
                        db: Session = Depends(get_db)):
    """
    Appele par service-ged avant toute lecture/telechargement d'un document
    administratif (Point 5). L'utilisateur doit d'abord avoir un droit
    structurel sur le groupe (son propre groupe, ou une branche qu'il
    supervise), PUIS fournir le bon code partage de ce groupe precis.
    """
    token = extraire_token(authorization)
    user  = get_user_from_token(token, db)
    perimetre = get_perimetre_utilisateur(db, user)

    groupe = db.query(GroupeService).filter_by(role_code=data.role_code).first()
    if not groupe:
        raise HTTPException(404, "Groupe de service introuvable")

    poste_ids_du_groupe = {m.poste_id for m in groupe.membres}
    a_le_droit_structurel = bool(poste_ids_du_groupe & set(perimetre["poste_ids"]))
    if not a_le_droit_structurel:
        raise HTTPException(403, "Vous n'avez pas de droit d'acces a ce service")

    if not groupe.code_acces_hash:
        raise HTTPException(400, "Aucun code de securite n'a encore ete defini pour ce service — contactez un administrateur")

    if not pwd_context.verify(data.code, groupe.code_acces_hash):
        raise HTTPException(401, "Code de securite incorrect")

    return VerifierCodeResponse(valide=True, role_code=groupe.role_code)


@router.get("/groupes-service", response_model=list[GroupeServiceOut],
            summary="Lister les groupes de service et leurs membres (admin)")
def list_groupes_service(authorization: Optional[str] = Header(None),
                         db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    groupes = db.query(GroupeService).all()
    return [
        GroupeServiceOut(
            id=g.id, role_code=g.role_code, label=g.label,
            description=g.description, branche=g.branche, couleur=g.couleur,
            code_defini=bool(g.code_acces_hash),
            membres=[
                GroupeServiceMembreOut(
                    poste_id=m.poste_id, label=m.label,
                    branche_supervisee=m.branche_supervisee
                ) for m in g.membres
            ],
        ) for g in groupes
    ]


@router.post("/groupes-service", response_model=GroupeServiceOut, status_code=201,
             summary="Creer un nouveau groupe de service (admin)")
def create_groupe_service(data: GroupeServiceCreate,
                          authorization: Optional[str] = Header(None),
                          db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    if db.query(GroupeService).filter_by(role_code=data.role_code).first():
        raise HTTPException(400, "Ce role_code existe deja")
    groupe = GroupeService(**data.model_dump())
    db.add(groupe); db.commit(); db.refresh(groupe)
    journaliser(db, "CREATE_GROUPE_SERVICE",
                f"Creation du groupe de service {groupe.role_code}", user_id=admin.id)
    return GroupeServiceOut(
        id=groupe.id, role_code=groupe.role_code, label=groupe.label,
        description=groupe.description, branche=groupe.branche, couleur=groupe.couleur,
        code_defini=False, membres=[],
    )


@router.put("/groupes-service/{groupe_id}", response_model=GroupeServiceOut,
            summary="Modifier un groupe de service (admin)")
def update_groupe_service(groupe_id: int, data: GroupeServiceUpdate,
                          authorization: Optional[str] = Header(None),
                          db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    groupe = db.get(GroupeService, groupe_id)
    if not groupe:
        raise HTTPException(404, "Groupe introuvable")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(groupe, field, value)
    db.commit(); db.refresh(groupe)
    return GroupeServiceOut(
        id=groupe.id, role_code=groupe.role_code, label=groupe.label,
        description=groupe.description, branche=groupe.branche, couleur=groupe.couleur,
        code_defini=bool(groupe.code_acces_hash),
        membres=[
            GroupeServiceMembreOut(poste_id=m.poste_id, label=m.label,
                                   branche_supervisee=m.branche_supervisee)
            for m in groupe.membres
        ],
    )


@router.put("/groupes-service/{groupe_id}/code",
            summary="Definir ou modifier le code de securite partage d'un groupe (admin)")
def definir_code_groupe(groupe_id: int, data: DefinirCodeRequest,
                        authorization: Optional[str] = Header(None),
                        db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    groupe = db.get(GroupeService, groupe_id)
    if not groupe:
        raise HTTPException(404, "Groupe introuvable")
    groupe.code_acces_hash = pwd_context.hash(data.code)
    db.commit()
    journaliser(db, "SET_CODE_GROUPE_SERVICE",
                f"Code de securite (re)defini pour {groupe.role_code}", user_id=admin.id)
    return {"message": f"Code de securite mis a jour pour {groupe.role_code}"}


@router.put("/groupes-service/{groupe_id}/membres",
            summary="Redefinir la liste des postes membres d'un groupe (admin)")
def definir_membres_groupe(groupe_id: int, data: MembresGroupeRequest,
                           authorization: Optional[str] = Header(None),
                           db: Session = Depends(get_db)):
    token = extraire_token(authorization)
    admin = get_user_from_token(token, db)
    require_admin_or_sous_admin(admin)
    groupe = db.get(GroupeService, groupe_id)
    if not groupe:
        raise HTTPException(404, "Groupe introuvable")

    conflits = (
        db.query(GroupeServiceMembre)
        .filter(GroupeServiceMembre.poste_id.in_(data.poste_ids),
                GroupeServiceMembre.groupe_id != groupe_id)
        .all()
    )
    if conflits:
        raise HTTPException(
            400,
            f"Poste(s) deja affecte(s) a un autre groupe : {[c.poste_id for c in conflits]}"
        )

    db.query(GroupeServiceMembre).filter_by(groupe_id=groupe_id).delete()
    for pid in data.poste_ids:
        db.add(GroupeServiceMembre(groupe_id=groupe_id, poste_id=pid))
    db.commit()
    journaliser(db, "UPDATE_MEMBRES_GROUPE_SERVICE",
                f"Membres du groupe {groupe.role_code} mis a jour : {data.poste_ids}",
                user_id=admin.id)
    return {"message": "Membres mis a jour", "poste_ids": data.poste_ids}
