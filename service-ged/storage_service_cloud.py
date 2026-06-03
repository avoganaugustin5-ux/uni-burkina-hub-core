"""
storage_service.py — version cloud (Render)
MinIO désactivé — stockage local /tmp/storage
Compatible avec le code existant sans modification des routes.
"""
import os
import shutil
from pathlib import Path

# Configuration
STORAGE_PATH = os.getenv("STORAGE_PATH", "/tmp/storage")
MINIO_ENABLED = False  # MinIO désactivé en cloud (Docker off)

# Client MinIO factice pour éviter les erreurs d'import
minio_client = None
bucket_name = "uniburkina-documents"


def init_storage():
    """Initialise le stockage local à la place de MinIO."""
    path = Path(STORAGE_PATH)
    path.mkdir(parents=True, exist_ok=True)
    (path / "documents").mkdir(exist_ok=True)
    (path / "plannings").mkdir(exist_ok=True)
    (path / "annonces").mkdir(exist_ok=True)
    print(f"[STORAGE] Stockage local initialisé : {STORAGE_PATH}")
    print("[STORAGE] MinIO désactivé (mode cloud Render)")


def save_file(file_content: bytes, filename: str, folder: str = "documents") -> str:
    """Sauvegarde un fichier localement et retourne son chemin."""
    folder_path = Path(STORAGE_PATH) / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    file_path = folder_path / filename
    with open(file_path, "wb") as f:
        f.write(file_content)
    return str(file_path)


def get_file(filename: str, folder: str = "documents") -> bytes:
    """Lit un fichier depuis le stockage local."""
    file_path = Path(STORAGE_PATH) / folder / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filename}")
    with open(file_path, "rb") as f:
        return f.read()


def delete_file(filename: str, folder: str = "documents") -> bool:
    """Supprime un fichier du stockage local."""
    file_path = Path(STORAGE_PATH) / folder / filename
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def get_file_url(filename: str, folder: str = "documents") -> str:
    """Retourne l'URL de téléchargement (via l'API GED)."""
    return f"/ged/documents/fichier/{folder}/{filename}"


def upload_to_minio(file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
    """Alias pour compatibilité — redirige vers save_file."""
    folder = object_name.split("/")[0] if "/" in object_name else "documents"
    filename = object_name.split("/")[-1]
    return save_file(file_content, filename, folder)


def download_from_minio(object_name: str) -> bytes:
    """Alias pour compatibilité — redirige vers get_file."""
    folder = object_name.split("/")[0] if "/" in object_name else "documents"
    filename = object_name.split("/")[-1]
    return get_file(filename, folder)
