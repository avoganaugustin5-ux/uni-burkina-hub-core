from pydantic import BaseModel
from typing import Optional, List, Any

class ResultatRecherche(BaseModel):
    total:     int
    resultats: List[dict]

class RechercheGlobaleResponse(BaseModel):
    query:     str
    total:     int
    documents: ResultatRecherche
    sujets:    ResultatRecherche

class IndexationDocument(BaseModel):
    id_doc:         int
    titre:          str
    type_ressource: str
    texte_ocr:      Optional[str] = None
    statut:         str = "VALIDE"
    id_filiere:     Optional[int] = None
    id_univ:        Optional[int] = None
    date_soumission: Optional[str] = None
    auteur_poste_id: Optional[str] = None  # AJOUT SECURITE UTS — cloisonnement recherche

class IndexationSujet(BaseModel):
    id_sujet:      int
    titre:         str
    contenu:       str
    categorie:     str = "AUTRE"
    statut:        str = "VISIBLE"
    id_filiere:    Optional[int] = None
    auteur_nom:    Optional[str] = None
    date_creation: Optional[str] = None

class SearchStats(BaseModel):
    index_documents: int
    index_sujets:    int
    es_status:       str