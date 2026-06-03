from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class StatutOCREnum(str, enum.Enum):
    EN_ATTENTE  = "EN_ATTENTE"
    EN_COURS    = "EN_COURS"
    TERMINE     = "TERMINE"
    ECHEC       = "ECHEC"

class DocumentOCR(Base):
    __tablename__ = "documents_ocr"

    id_ocr           = Column(Integer, primary_key=True, autoincrement=True)
    nom_fichier_orig = Column(String(300), nullable=False)
    chemin_source    = Column(String(500), nullable=False)
    chemin_pdf       = Column(String(500), nullable=True)
    texte_extrait    = Column(Text, nullable=True)
    nb_pages         = Column(Integer, default=1)
    taille_fichier   = Column(BigInteger, nullable=True)
    statut           = Column(String(20), default=StatutOCREnum.EN_ATTENTE)
    langue           = Column(String(10), default="fra")
    message_erreur   = Column(Text, nullable=True)
    date_soumission  = Column(DateTime, default=datetime.utcnow)
    date_traitement  = Column(DateTime, nullable=True)
    id_doc_ged       = Column(Integer, nullable=True)