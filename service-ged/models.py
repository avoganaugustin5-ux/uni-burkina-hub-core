from sqlalchemy import (Column, String, Boolean, DateTime,
                        ForeignKey, Enum, Integer, Text, BigInteger)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid, enum

Base = declarative_base()

# ── Enums ──────────────────────────────────────────────────
class TypeRessourceEnum(str, enum.Enum):
    COURS   = "COURS"
    TD      = "TD"
    EXAMEN  = "EXAMEN"
    ARCHIVE = "ARCHIVE"

class StatutDocumentEnum(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REFUSE     = "REFUSE"

# ── Document ───────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id_doc           = Column(Integer, primary_key=True, autoincrement=True)
    titre            = Column(String(300), nullable=False)
    type_ressource   = Column(Enum(TypeRessourceEnum), nullable=False)
    chemin_fichier   = Column(String(500), nullable=False)  # chemin local
    nom_fichier      = Column(String(300), nullable=True)
    taille_fichier   = Column(BigInteger, nullable=True)    # en octets
    type_mime        = Column(String(100), nullable=True)
    texte_ocr        = Column(Text, nullable=True)
    est_valide       = Column(Boolean, default=False)
    statut           = Column(Enum(StatutDocumentEnum),
                              default=StatutDocumentEnum.EN_ATTENTE)
    motif_refus      = Column(Text, nullable=True)
    date_soumission  = Column(DateTime, default=datetime.utcnow)
    date_publication = Column(DateTime, nullable=True)

    # Relations
    id_module        = Column(Integer, nullable=True)
    id_filiere       = Column(Integer, nullable=True)
    id_univ          = Column(Integer, nullable=True)
    uploaded_by      = Column(UUID(as_uuid=True), nullable=True)
    valide_par       = Column(UUID(as_uuid=True), nullable=True)

# ── Planning ───────────────────────────────────────────────
class Planning(Base):
    __tablename__ = "plannings"

    id_planning    = Column(Integer, primary_key=True, autoincrement=True)
    semaine        = Column(String(50), nullable=False)
    titre          = Column(String(200), nullable=False)
    fichier_url    = Column(String(500), nullable=True)
    date_envoi     = Column(DateTime, default=datetime.utcnow)
    id_filiere     = Column(Integer, nullable=True)
    id_univ        = Column(Integer, nullable=True)
    publie_par     = Column(UUID(as_uuid=True), nullable=True)
    est_publie     = Column(Boolean, default=False)

# ── Annonce ────────────────────────────────────────────────
class Annonce(Base):
    __tablename__ = "annonces"

    id_annonce    = Column(Integer, primary_key=True, autoincrement=True)
    titre         = Column(String(200), nullable=False)
    contenu       = Column(Text, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)
    est_publiee   = Column(Boolean, default=False)
    id_univ       = Column(Integer, nullable=True)
    id_filiere    = Column(Integer, nullable=True)
    publie_par    = Column(UUID(as_uuid=True), nullable=True)