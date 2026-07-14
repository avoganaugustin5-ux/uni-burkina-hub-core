from elasticsearch import Elasticsearch
import os

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
es = Elasticsearch(ES_URL)

# ── Noms des index ─────────────────────────────────────────
INDEX_DOCUMENTS = "uniburkina_documents"
INDEX_SUJETS    = "uniburkina_sujets"

# ══════════════════════════════════════════════════════════
# CREATION DES INDEX
# ══════════════════════════════════════════════════════════
def creer_index_documents():
    if not es.indices.exists(index=INDEX_DOCUMENTS):
        es.indices.create(index=INDEX_DOCUMENTS, body={
            "settings": {
                "analysis": {
                    "analyzer": {
                        "french_analyzer": {
                            "type": "standard",
                            "stopwords": "_french_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id_doc":         {"type": "integer"},
                    "titre":          {"type": "text", "analyzer": "french_analyzer"},
                    "type_ressource": {"type": "keyword"},
                    "texte_ocr":      {"type": "text", "analyzer": "french_analyzer"},
                    "statut":         {"type": "keyword"},
                    "id_filiere":     {"type": "integer"},
                    "id_univ":        {"type": "integer"},
                    "date_soumission":{"type": "date"},
                    # AJOUT SECURITE UTS — poste propriétaire (via circuit), utilisé
                    # pour le cloisonnement des documents ADMINISTRATIF en recherche.
                    "auteur_poste_id":{"type": "keyword"},
                }
            }
        })
        print(f"Index '{INDEX_DOCUMENTS}' cree")
    else:
        # AJOUT SECURITE UTS — migration additive : l'ajout d'un champ à un
        # mapping existant est sans risque et ne nécessite pas de réindexation
        # complète (les documents déjà indexés auront simplement ce champ vide,
        # ce qui les exclut par défaut des résultats ADMINISTRATIF — fail-closed).
        es.indices.put_mapping(index=INDEX_DOCUMENTS, body={
            "properties": {
                "auteur_poste_id": {"type": "keyword"}
            }
        })


def creer_index_sujets():
    if not es.indices.exists(index=INDEX_SUJETS):
        es.indices.create(index=INDEX_SUJETS, body={
            "mappings": {
                "properties": {
                    "id_sujet":       {"type": "integer"},
                    "titre":          {"type": "text", "analyzer": "standard"},
                    "contenu":        {"type": "text", "analyzer": "standard"},
                    "categorie":      {"type": "keyword"},
                    "statut":         {"type": "keyword"},
                    "id_filiere":     {"type": "integer"},
                    "auteur_nom":     {"type": "text"},
                    "date_creation":  {"type": "date"},
                }
            }
        })
        print(f"Index '{INDEX_SUJETS}' cree")


def init_elasticsearch():
    try:
        creer_index_documents()
        creer_index_sujets()
        print("Elasticsearch initialise")
    except Exception as e:
        print(f"AVERTISSEMENT : Elasticsearch non disponible : {e}")


# ══════════════════════════════════════════════════════════
# INDEXATION
# ══════════════════════════════════════════════════════════
def indexer_document(doc: dict):
    es.index(index=INDEX_DOCUMENTS, id=doc["id_doc"], document=doc)

def indexer_sujet(sujet: dict):
    es.index(index=INDEX_SUJETS, id=sujet["id_sujet"], document=sujet)

def supprimer_document(id_doc: int):
    try:
        es.delete(index=INDEX_DOCUMENTS, id=id_doc)
    except Exception:
        pass

def supprimer_sujet(id_sujet: int):
    try:
        es.delete(index=INDEX_SUJETS, id=id_sujet)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
# RECHERCHE
# ══════════════════════════════════════════════════════════
def rechercher_documents(
    q: str,
    type_ressource: str = None,
    id_filiere: int = None,
    page: int = 1,
    limite: int = 10,
    postes_visibles: list = None,
    is_admin: bool = False
) -> dict:
    must = [{"multi_match": {
        "query": q,
        "fields": ["titre^3", "texte_ocr"],
        "fuzziness": "AUTO"
    }}]

    filters = [{"term": {"statut": "VALIDE"}}]
    if type_ressource:
        filters.append({"term": {"type_ressource": type_ressource}})
    if id_filiere:
        filters.append({"term": {"id_filiere": id_filiere}})

    # AJOUT SECURITE UTS — cloisonnement des documents ADMINISTRATIF (Point 4) :
    # un non-admin ne voit un document ADMINISTRATIF dans les résultats que si
    # son poste appartient au périmètre du service propriétaire (même logique
    # que list_documents côté service-ged). Les autres types de documents ne
    # sont pas concernés par cette restriction. ADMIN/SOUS_ADMIN : illimité.
    if not is_admin:
        filters.append({
            "bool": {
                "should": [
                    {"bool": {"must_not": {"term": {"type_ressource": "ADMINISTRATIF"}}}},
                    {"bool": {"must": [
                        {"term": {"type_ressource": "ADMINISTRATIF"}},
                        {"terms": {"auteur_poste_id": postes_visibles or []}}
                    ]}}
                ],
                "minimum_should_match": 1
            }
        })

    body = {
        "query": {"bool": {"must": must, "filter": filters}},
        "highlight": {
            "fields": {
                "titre":     {"number_of_fragments": 0},
                "texte_ocr": {"fragment_size": 150, "number_of_fragments": 2}
            }
        },
        "from": (page - 1) * limite,
        "size": limite
    }

    res = es.search(index=INDEX_DOCUMENTS, body=body)
    return _formater_resultats(res)


def rechercher_sujets(
    q: str,
    categorie: str = None,
    id_filiere: int = None,
    page: int = 1,
    limite: int = 10
) -> dict:
    must = [{"multi_match": {
        "query": q,
        "fields": ["titre^2", "contenu"],
        "fuzziness": "AUTO"
    }}]

    filters = [{"term": {"statut": "VISIBLE"}}]
    if categorie:
        filters.append({"term": {"categorie": categorie}})
    if id_filiere:
        filters.append({"term": {"id_filiere": id_filiere}})

    body = {
        "query": {"bool": {"must": must, "filter": filters}},
        "highlight": {
            "fields": {
                "titre":   {"number_of_fragments": 0},
                "contenu": {"fragment_size": 150, "number_of_fragments": 2}
            }
        },
        "from": (page - 1) * limite,
        "size": limite
    }

    res = es.search(index=INDEX_SUJETS, body=body)
    return _formater_resultats(res)


def recherche_globale(q: str, page: int = 1, limite: int = 10, postes_visibles: list = None, is_admin: bool = False) -> dict:
    """Recherche simultanee dans documents ET sujets."""
    docs   = rechercher_documents(q, page=page, limite=limite // 2 or 5,
                                   postes_visibles=postes_visibles, is_admin=is_admin)
    sujets = rechercher_sujets(q, page=page, limite=limite // 2 or 5)
    return {
        "query":     q,
        "documents": docs,
        "sujets":    sujets,
        "total":     docs["total"] + sujets["total"]
    }


def _formater_resultats(res: dict) -> dict:
    hits = res["hits"]
    resultats = []
    for hit in hits["hits"]:
        item = hit["_source"]
        item["_score"]     = hit["_score"]
        item["_highlight"] = hit.get("highlight", {})
        resultats.append(item)
    return {
        "total":     hits["total"]["value"],
        "resultats": resultats
    }