from sqlalchemy import (Column, String, Boolean, DateTime,
                        ForeignKey, Enum, Integer, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid, enum

Base = declarative_base()

# ── Enums ──────────────────────────────────────────────────
class RoleEnum(str, enum.Enum):
    ADMIN            = "ADMIN"
    PRESIDENT        = "PRESIDENT"
    SOUS_ADMIN       = "SOUS_ADMIN"
    ENSEIGNANT       = "ENSEIGNANT"
    DELEGUE          = "DELEGUE"
    ETUDIANT         = "ETUDIANT"
    # ── AJOUT UTS — acteurs de l'organigramme (Président/Cabinet/VP/SG/Directeurs/Services) ──
    CHEF_DEPARTEMENT = "CHEF_DEPARTEMENT"  # deja utilise dans frontend/main.py mais absent ici (bug corrige)
    VP_EIP           = "VP_EIP"            # Vice-President Enseignements, Innovations Pedagogiques
    VP_RCU           = "VP_RCU"            # Vice-President Recherche et Cooperation Universitaire
    SG               = "SG"                # Secretaire General
    CABINET          = "CABINET"           # CCAB, CJ, PRCP + tous les services du Cabinet
    DIRECTEUR        = "DIRECTEUR"         # DSI, DEI, DPE, DAOI, DRV, DCPE, DPRUE, DAF, DEP, DRH, BCMP, BUC...
    EMPLOYE          = "EMPLOYE"           # Tout employe de service, regroupe par direction (SSM, SEAp, SAF...)

class SexeEnum(str, enum.Enum):
    HOMME = "HOMME"
    FEMME = "FEMME"

class TypeIdentiteEnum(str, enum.Enum):
    CNIB      = "CNIB"
    PASSEPORT = "PASSEPORT"
    PERMIS    = "PERMIS"

class TypeRessourceEnum(str, enum.Enum):
    COURS   = "COURS"
    TD      = "TD"
    EXAMEN  = "EXAMEN"
    ARCHIVE = "ARCHIVE"

# ── Université ─────────────────────────────────────────────
class Universite(Base):
    __tablename__ = "universites"

    id_univ      = Column(Integer, primary_key=True, autoincrement=True)
    nom_univ     = Column(String(200), nullable=False, unique=True)
    localisation = Column(String(300), nullable=True)
    actif        = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    ufrs         = relationship("UFR", back_populates="universite")
    utilisateurs = relationship("Utilisateur", back_populates="universite")

# ── UFR ────────────────────────────────────────────────────
class UFR(Base):
    __tablename__ = "ufrs"

    id_ufr   = Column(Integer, primary_key=True, autoincrement=True)
    nom_ufr  = Column(String(200), nullable=False)
    code_ufr = Column(String(20), nullable=False, unique=True)
    id_univ  = Column(Integer, ForeignKey("universites.id_univ"), nullable=False)

    universite = relationship("Universite", back_populates="ufrs")
    filieres   = relationship("Filiere", back_populates="ufr")

# ── Filière ────────────────────────────────────────────────
class Filiere(Base):
    __tablename__ = "filieres"

    id_filiere  = Column(Integer, primary_key=True, autoincrement=True)
    nom_filiere = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    id_ufr      = Column(Integer, ForeignKey("ufrs.id_ufr"), nullable=False)

    ufr     = relationship("UFR", back_populates="filieres")
    modules = relationship("Module", back_populates="filiere")

# ── Module ─────────────────────────────────────────────────
class Module(Base):
    __tablename__ = "modules"

    id_module   = Column(Integer, primary_key=True, autoincrement=True)
    code_module = Column(String(50), nullable=False, unique=True)
    libelle     = Column(String(200), nullable=False)
    coefficient = Column(Integer, default=1)
    id_filiere  = Column(Integer, ForeignKey("filieres.id_filiere"), nullable=False)

    filiere      = relationship("Filiere", back_populates="modules")
    affectations = relationship("AffectationEnseignant", back_populates="module")

# ── Utilisateur (table principale) ────────────────────────
class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom              = Column(String(100), nullable=False)
    prenom           = Column(String(100), nullable=False)
    sexe             = Column(Enum(SexeEnum), nullable=True)
    nationalite      = Column(String(100), nullable=True)
    date_naissance   = Column(DateTime, nullable=True)
    lieu_naissance   = Column(String(200), nullable=True)
    ville_actuelle   = Column(String(200), nullable=True)
    telephone        = Column(String(20), nullable=True)
    email            = Column(String(200), unique=True, nullable=False)
    username         = Column(String(100), unique=True, nullable=False)
    mot_de_passe     = Column(String, nullable=False)
    role             = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.ETUDIANT)
    photo_profil_url = Column(String(500), nullable=True)   # URL MinIO
    actif            = Column(Boolean, default=True)
    tentatives_connexion = Column(Integer, default=0)       # Sécurité anti-bruteforce
    date_inscription = Column(DateTime, default=datetime.utcnow)
    derniere_connexion = Column(DateTime, nullable=True)

    # Clé étrangère université
    id_univ    = Column(Integer, ForeignKey("universites.id_univ"), nullable=True)
    universite = relationship("Universite", back_populates="utilisateurs")

    # ── AJOUT UTS — poste precis dans l'organigramme (cf. frontend/static/js/uts_org_data.js) ──
    # poste_id   : identifiant du poste dans UTS_ORG (ex: 'ssm','dsi','ccab','president'...)
    #              utilise pour le routage documentaire (Objectif 1.2) et l'affichage du Dashboard.
    # branche    : Presidence / Cabinet / VP-EIP / VP-RCU / SG (repris de UTS_ORG.branche)
    # type_poste : 'individuel' / 'service' / 'directeur' (repris de UTS_ORG.type)
    # id_ufr_gere: pour role=CHEF_DEPARTEMENT uniquement — l'UFR dont cette personne est chef.
    #              Permet le routage automatique etudiant -> chef de departement (Objectif 1.1).
    poste_id    = Column(String(50), nullable=True)
    branche     = Column(String(50), nullable=True)
    type_poste  = Column(String(30), nullable=True)
    id_ufr_gere = Column(Integer, ForeignKey("ufrs.id_ufr"), nullable=True)

    # Relations
    identite      = relationship("Identite", back_populates="utilisateur", uselist=False)
    notifications = relationship("Notification", back_populates="utilisateur")

# ── Identité (CNIB / Passeport / Matricule) ───────────────
class Identite(Base):
    __tablename__ = "identites"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    type_identite    = Column(Enum(TypeIdentiteEnum), nullable=False)
    numero_identite  = Column(String(100), nullable=False)
    numero_matricule = Column(String(100), nullable=True)  # Matricule UTS
    user_id          = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"), unique=True)

    utilisateur = relationship("Utilisateur", back_populates="identite")

# ── Notification ───────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id_notif  = Column(Integer, primary_key=True, autoincrement=True)
    titre     = Column(String(200), nullable=False)
    message   = Column(Text, nullable=False)
    est_lue   = Column(Boolean, default=False)
    date_envoi = Column(DateTime, default=datetime.utcnow)
    user_id   = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))

    utilisateur = relationship("Utilisateur", back_populates="notifications")

# ── AffectationEnseignant ──────────────────────────────────
class AffectationEnseignant(Base):
    __tablename__ = "affectations_enseignants"

    id_affectation   = Column(Integer, primary_key=True, autoincrement=True)
    date_affectation = Column(DateTime, default=datetime.utcnow)
    semestre         = Column(String(50), nullable=True)
    enseignant_id    = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    id_module        = Column(Integer, ForeignKey("modules.id_module"))

    module = relationship("Module", back_populates="affectations")

# ── InscriptionEtudiant ────────────────────────────────────
class InscriptionEtudiant(Base):
    __tablename__ = "inscriptions_etudiants"

    id_inscription    = Column(Integer, primary_key=True, autoincrement=True)
    annee_academique  = Column(String(20), nullable=False)
    niveau_etude      = Column(String(50), nullable=True)   # L1, L2, L3, M1, M2
    statut            = Column(Boolean, default=True)
    etudiant_id       = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    id_filiere        = Column(Integer, ForeignKey("filieres.id_filiere"))
    id_univ           = Column(Integer, ForeignKey("universites.id_univ"))

# ── Journal d'Audit ────────────────────────────────────────
class JournalAudit(Base):
    __tablename__ = "journal_audit"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    action      = Column(String(200), nullable=False)  # LOGIN, LOGOUT, CREATE_USER...
    description = Column(Text, nullable=True)
    ip_address  = Column(String(50), nullable=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"), nullable=True)
    date_action = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════
# AJOUT SECURITE UTS — Cloisonnement documentaire par service (Point 4/5)
# ══════════════════════════════════════════════════════════
#
# Un "groupe de service" = un pool documentaire partagé (ex: EMPLOYE_DSI
# regroupe dsi+seap+srss+ssm+sp-vpeip). Decision validee : le "service" du
# point 4 correspond a ce niveau de regroupement (toute une direction),
# pas au poste_id individuel.
#
# Chaque poste_id appartient a EXACTEMENT UN groupe (contrainte unique sur
# GroupeServiceMembre.poste_id). Un utilisateur sans poste_id (etudiant,
# enseignant...) n'est concerne par aucun cloisonnement de ce type.
#
# branche_supervisee : rempli UNIQUEMENT pour les postes "chefs de branche"
# (vp-eip, vp-rcu, sg -- decision validee : vision globale sur toute leur
# branche). Quand rempli, l'utilisateur voit EN PLUS tous les groupes dont
# le champ GroupeService.branche correspond a cette valeur.
# Le Chef de Cabinet (ccab) n'a pas besoin de ce champ : il est deja membre
# du groupe CABINET, qui contient a plat tout le Cabinet (cascade PRCP incluse).

class GroupeService(Base):
    __tablename__ = "groupes_service"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    role_code         = Column(String(50), unique=True, nullable=False)   # ex: 'EMPLOYE_DSI', 'CABINET'
    label             = Column(String(200), nullable=False)
    description       = Column(String(300), nullable=True)
    branche           = Column(String(50), nullable=True)                 # 'VP-EIP' / 'VP-RCU' / 'SG' / 'Cabinet' / None
    couleur           = Column(String(20), nullable=True)
    code_acces_hash   = Column(String(255), nullable=True)                # bcrypt -- jamais stocke en clair
    date_creation     = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    membres = relationship("GroupeServiceMembre", back_populates="groupe",
                           cascade="all, delete-orphan")


class GroupeServiceMembre(Base):
    __tablename__ = "groupes_service_membres"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    groupe_id           = Column(Integer, ForeignKey("groupes_service.id"), nullable=False)
    poste_id            = Column(String(50), nullable=False, unique=True)   # un poste_id -> un seul groupe
    label               = Column(String(200), nullable=True)                # libelle lisible (snapshot organigramme)
    # Rempli uniquement pour un "chef de branche" (vp-eip, vp-rcu, sg) : la
    # branche entiere qu'il supervise en plus de son propre groupe (DIRECTION).
    branche_supervisee  = Column(String(50), nullable=True)

    groupe = relationship("GroupeService", back_populates="membres")