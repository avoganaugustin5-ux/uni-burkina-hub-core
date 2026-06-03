from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OCRResponse(BaseModel):
    id_ocr:           int
    nom_fichier_orig: str
    texte_extrait:    Optional[str]
    nb_pages:         int
    statut:           str
    langue:           str
    chemin_pdf:       Optional[str]
    message_erreur:   Optional[str]
    date_soumission:  datetime
    date_traitement:  Optional[datetime]
    id_doc_ged:       Optional[int]

    class Config:
        from_attributes = True

class OCRStats(BaseModel):
    total_traites:  int
    total_termines: int
    total_echecs:   int
    total_attente:  int