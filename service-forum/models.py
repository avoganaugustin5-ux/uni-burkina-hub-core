from sqlalchemy import (Column, String, Boolean, DateTime,
                        Integer, Text, ForeignKey, Enum)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid, enum

Base = declarative_base()

class StatutPostEnum(str, enum.Enum):
    VISIBLE  = "VISIBLE"
    MASQUE   = "MASQUE"
    SIGNALE  = "SIGNALE"

class CategorieEnum(str, enum.Enum):
    COURS    = "COURS"
    EXAMEN   = "EXAMEN"
    STAGE    = "STAGE"
    VIE_UNI  = "VIE_UNI"
    AUTRE    = "AUTRE"

# ── Sujet (fil de discussion) ──────────────────────────────
class Sujet(Base):
    __tablename__ = "sujets"

    id_sujet      = Column(Integer, primary_key=True, autoincrement=True)
    titre         = Column(String(300), nullable=False)
    contenu       = Column(Text, nullable=False)
    categorie     = Column(Enum(CategorieEnum), default=CategorieEnum.AUTRE)
    statut        = Column(Enum(StatutPostEnum), default=StatutPostEnum.VISIBLE)
    est_epingle   = Column(Boolean, default=False)
    est_resolu    = Column(Boolean, default=False)
    nb_vues       = Column(Integer, default=0)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modif    = Column(DateTime, nullable=True)

    # Liens (sans FK réelle inter-services)
    id_filiere    = Column(Integer, nullable=True)
    id_univ       = Column(Integer, nullable=True)
    auteur_id     = Column(UUID(as_uuid=True), nullable=True)
    auteur_nom    = Column(String(100), nullable=True)  # dénormalisé

    # Relation
    reponses      = relationship("Reponse", back_populates="sujet",
                                  cascade="all, delete-orphan")

# ── Réponse ────────────────────────────────────────────────
class Reponse(Base):
    __tablename__ = "reponses"

    id_reponse    = Column(Integer, primary_key=True, autoincrement=True)
    contenu       = Column(Text, nullable=False)
    statut        = Column(Enum(StatutPostEnum), default=StatutPostEnum.VISIBLE)
    est_solution  = Column(Boolean, default=False)  # réponse acceptée
    nb_likes      = Column(Integer, default=0)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modif    = Column(DateTime, nullable=True)

    id_sujet      = Column(Integer, ForeignKey("sujets.id_sujet"), nullable=False)
    auteur_id     = Column(UUID(as_uuid=True), nullable=True)
    auteur_nom    = Column(String(100), nullable=True)

    sujet         = relationship("Sujet", back_populates="reponses")

# ── Signalement ────────────────────────────────────────────
class Signalement(Base):
    __tablename__ = "signalements"

    id_signalement = Column(Integer, primary_key=True, autoincrement=True)
    raison         = Column(Text, nullable=False)
    date_signalement = Column(DateTime, default=datetime.utcnow)
    traite         = Column(Boolean, default=False)

    # cible : sujet OU réponse
    id_sujet       = Column(Integer, nullable=True)
    id_reponse     = Column(Integer, nullable=True)
    signale_par    = Column(UUID(as_uuid=True), nullable=True)