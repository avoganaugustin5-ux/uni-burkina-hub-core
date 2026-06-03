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