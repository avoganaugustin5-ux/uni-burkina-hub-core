"""
storage_service.py — version cloud (Render)
MinIO désactivé — stockage local /tmp/storage
Fonctions identiques à la version MinIO pour compatibilité totale.
"""
import os
import shutil
from pathlib import Path

STORAGE_PATH = os.getenv("STORAGE_PATH", "/tmp/storage")

def init_storage():
    """Initialise les dossiers de stockage local."""
    for folder in ["documents", "plannings", "annonces", "temp"]:
        Path(STORAGE_PATH, folder).mkdir(parents=True, exist_ok=True)
    print(f"[STORAGE] Stockage local initialisé : {STORAGE_PATH}")
    print("[STORAGE] MinIO désactivé — mode cloud Render")

def upload_fichier(contenu: bytes, nom_fichier: str, dossier: str = "documents") -> str:
    """Sauvegarde un fichier et retourne son chemin relatif."""
    dossier_path = Path(STORAGE_PATH) / dossier
    dossier_path.mkdir(parents=True, exist_ok=True)
    chemin = dossier_path / nom_fichier
    with open(chemin, "wb") as f:
        f.write(contenu)
    print(f"[STORAGE] Fichier sauvegardé : {dossier}/{nom_fichier}")
    return f"{dossier}/{nom_fichier}"

def supprimer_fichier(nom_fichier: str, dossier: str = "documents") -> bool:
    """Supprime un fichier du stockage local."""
    chemin = Path(STORAGE_PATH) / dossier / nom_fichier
    if chemin.exists():
        chemin.unlink()
        print(f"[STORAGE] Fichier supprimé : {dossier}/{nom_fichier}")
        return True
    return False

def fichier_existe(nom_fichier: str, dossier: str = "documents") -> bool:
    """Vérifie si un fichier existe dans le stockage local."""
    chemin = Path(STORAGE_PATH) / dossier / nom_fichier
    return chemin.exists()

def lister_fichiers(dossier: str = "documents") -> list:
    """Liste tous les fichiers d'un dossier."""
    dossier_path = Path(STORAGE_PATH) / dossier
    if not dossier_path.exists():
        return []
    return [f.name for f in dossier_path.iterdir() if f.is_file()]

def valider_fichier(nom_fichier: str, dossier: str = "documents") -> dict:
    """Retourne les métadonnées d'un fichier (taille, existence)."""
    chemin = Path(STORAGE_PATH) / dossier / nom_fichier
    if not chemin.exists():
        return {"existe": False, "taille": 0, "nom": nom_fichier}
    stat = chemin.stat()
    return {
        "existe": True,
        "taille": stat.st_size,
        "nom": nom_fichier,
        "chemin": str(chemin)
    }

def telecharger_fichier(nom_fichier: str, dossier: str = "documents") -> bytes:
    """Lit et retourne le contenu d'un fichier."""
    chemin = Path(STORAGE_PATH) / dossier / nom_fichier
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {dossier}/{nom_fichier}")
    with open(chemin, "rb") as f:
        return f.read()
