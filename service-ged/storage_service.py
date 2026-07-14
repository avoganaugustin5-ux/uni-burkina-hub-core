# ==============================================================================
# service-ged/storage_service.py — UniBurkina Hub
# VERSION MINIO — Remplace le stockage local disk
# Compatible drop-in : même interface que l'ancienne version locale
# Prérequis : pip install minio --break-system-packages
# MinIO doit tourner sur localhost:9000 (standalone .exe Windows)
# ==============================================================================

import os
import io
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

# ── Connexion MinIO ─────────────────────────────────────────
MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT",   "localhost:9000")
MINIO_ACCESS    = os.getenv("MINIO_ACCESS_KEY",  "minioadmin")   # corrigé : était MINIO_ROOT_USER
MINIO_SECRET    = os.getenv("MINIO_SECRET_KEY",  "minioadmin")   # corrigé : était MINIO_ROOT_PASSWORD
MINIO_SECURE    = os.getenv("MINIO_SECURE", "false").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=MINIO_SECURE,
)

# ── Buckets utilisés par service-ged ───────────────────────
BUCKETS = {
    "documents": "uniburkina-documents",
    "plannings": "uniburkina-plannings",
    "annonces":  "uniburkina-annonces",
    "profils":   "uniburkina-profils",
}

# ── Types de fichiers autorisés ─────────────────────────────
TYPES_AUTORISES = {
    ".pdf":  "application/pdf",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

TAILLE_MAX_MB = 50


# ==============================================================================
# INITIALISATION — Créer les buckets si inexistants
# ==============================================================================

def init_storage():
    """Crée les buckets MinIO s'ils n'existent pas encore."""
    for alias, bucket_name in BUCKETS.items():
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                print(f"[MinIO] Bucket créé : {bucket_name}")
            else:
                print(f"[MinIO] Bucket existant : {bucket_name}")
        except S3Error as e:
            print(f"[MinIO] Erreur bucket {bucket_name} : {e}")
    print(f"[MinIO] Stockage initialisé sur {MINIO_ENDPOINT}")


# ==============================================================================
# UPLOAD FICHIER
# ==============================================================================

async def upload_fichier(
    file: UploadFile,
    bucket: str = "documents",
    sous_dossier: str = ""
) -> dict:
    """
    Upload un fichier UploadFile vers MinIO.
    Retourne un dict compatible avec l'ancienne interface locale :
      { nom_original, nom_fichier, chemin_fichier,
        taille_fichier, type_mime, bucket, date_upload }

    chemin_fichier contient la CLÉ MinIO (ex: "cours/abc123.pdf").
    C'est ce qui est stocké en BDD dans Document.chemin_fichier.
    """
    if bucket not in BUCKETS:
        raise ValueError(f"Bucket inconnu : {bucket}")

    bucket_name  = BUCKETS[bucket]
    extension    = Path(file.filename or "fichier").suffix.lower()
    nom_unique   = f"{uuid.uuid4().hex}{extension}"
    objet_key    = f"{sous_dossier}/{nom_unique}" if sous_dossier else nom_unique

    contenu      = await file.read()
    taille       = len(contenu)
    content_type = file.content_type or "application/octet-stream"

    minio_client.put_object(
        bucket_name,
        objet_key,
        io.BytesIO(contenu),
        taille,
        content_type=content_type,
    )

    await file.seek(0)

    return {
        "nom_original":   file.filename,
        "nom_fichier":    nom_unique,
        "chemin_fichier": objet_key,
        "taille_fichier": taille,
        "type_mime":      content_type,
        "bucket":         bucket,
        "date_upload":    datetime.utcnow().isoformat(),
    }


# ==============================================================================
# TÉLÉCHARGEMENT (retourne bytes)
# ==============================================================================

def telecharger_fichier_bytes(chemin_fichier: str, bucket: str = "documents") -> bytes:
    """Télécharge un objet MinIO et retourne son contenu en bytes."""
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    try:
        response = minio_client.get_object(bucket_name, chemin_fichier)
        return response.read()
    except S3Error as e:
        raise FileNotFoundError(f"Fichier MinIO introuvable : {chemin_fichier} — {e}")


# ==============================================================================
# URL PRÉSIGNÉE
# ==============================================================================

def url_presignee(
    chemin_fichier: str,
    bucket: str = "documents",
    expire_minutes: int = 60
) -> str:
    """Génère une URL présignée MinIO valable expire_minutes minutes."""
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    return minio_client.presigned_get_object(
        bucket_name,
        chemin_fichier,
        expires=timedelta(minutes=expire_minutes),
    )


# ==============================================================================
# SUPPRESSION
# ==============================================================================

def supprimer_fichier(chemin_fichier: str, bucket: str = "documents") -> bool:
    """Supprime un objet de MinIO. Compatible ancienne interface."""
    if not chemin_fichier:
        return False
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    try:
        minio_client.remove_object(bucket_name, chemin_fichier)
        return True
    except S3Error:
        return False


# ==============================================================================
# EXISTENCE
# ==============================================================================

def fichier_existe(chemin_fichier: str, bucket: str = "documents") -> bool:
    """Vérifie si un objet existe dans MinIO. Compatible ancienne interface."""
    if not chemin_fichier:
        return False
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    try:
        minio_client.stat_object(bucket_name, chemin_fichier)
        return True
    except S3Error:
        return False


# ==============================================================================
# INFOS FICHIER
# ==============================================================================

def infos_fichier(chemin_fichier: str, bucket: str = "documents") -> dict:
    """Retourne les métadonnées d'un objet MinIO."""
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    try:
        stat = minio_client.stat_object(bucket_name, chemin_fichier)
        return {
            "nom_fichier":       Path(chemin_fichier).name,
            "taille_fichier":    stat.size,
            "date_modification": stat.last_modified.isoformat() if stat.last_modified else None,
            "content_type":      stat.content_type,
        }
    except S3Error:
        return {}


# ==============================================================================
# LISTER FICHIERS
# ==============================================================================

def lister_fichiers(bucket: str = "documents") -> list:
    """Liste les objets d'un bucket MinIO. Compatible ancienne interface."""
    bucket_name = BUCKETS.get(bucket, BUCKETS["documents"])
    try:
        objets = minio_client.list_objects(bucket_name, recursive=True)
        return [obj.object_name for obj in objets]
    except S3Error:
        return []


# ==============================================================================
# VALIDATION FICHIER (inchangée)
# ==============================================================================

def valider_fichier(file: UploadFile) -> tuple[bool, str]:
    """Valide le type d'un fichier uploadé. Retourne (valide, message)."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in TYPES_AUTORISES:
        return False, (
            f"Type non autorisé : {extension}. "
            f"Types autorisés : {list(TYPES_AUTORISES.keys())}"
        )
    return True, "Fichier valide"
