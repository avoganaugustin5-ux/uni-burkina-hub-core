# ==============================================================================
# service-ocr/ocr_storage_minio.py — UniBurkina Hub
# Module de stockage MinIO pour service-ocr
# Remplace les opérations UPLOAD_DIR / OUTPUT_DIR du main.py
# Prérequis : pip install minio --break-system-packages
# ==============================================================================

import os
import io
import uuid
import tempfile
from pathlib import Path
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

# ── Connexion MinIO ─────────────────────────────────────────
MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT",    "localhost:9000")
MINIO_ACCESS    = os.getenv("MINIO_ROOT_USER",    "uniburkina_admin")
MINIO_SECRET    = os.getenv("MINIO_ROOT_PASSWORD","UTS_Minio2025!")
MINIO_SECURE    = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Client lazy — créé à la première utilisation pour ne pas bloquer le démarrage
_minio_client = None

def minio_client():
    """Retourne le client MinIO (connexion lazy)."""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS,
            secret_key=MINIO_SECRET,
            secure=MINIO_SECURE,
        )
    return _minio_client

# ── Buckets OCR ─────────────────────────────────────────────
BUCKET_UPLOADS  = "uniburkina-ocr-uploads"   # images sources uploadées
BUCKET_OUTPUTS  = "uniburkina-ocr-output"    # PDF/DOCX/XLSX/PPTX/TXT/MD générés

# ── Dossiers temporaires locaux (nécessaires pour ReportLab, Pillow, cv2) ─────
# Ces dossiers servent de zone de travail temporaire UNIQUEMENT.
# Les fichiers finaux sont uploadés vers MinIO puis supprimés localement.
_TMP_UPLOAD = Path(tempfile.gettempdir()) / "uniburkina_ocr_uploads"
_TMP_OUTPUT = Path(tempfile.gettempdir()) / "uniburkina_ocr_outputs"
_TMP_UPLOAD.mkdir(parents=True, exist_ok=True)
_TMP_OUTPUT.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# INITIALISATION BUCKETS
# ==============================================================================

def init_ocr_storage():
    """Crée les buckets MinIO OCR s'ils n'existent pas encore."""
    for bucket in [BUCKET_UPLOADS, BUCKET_OUTPUTS]:
        try:
            if not minio_client().bucket_exists(bucket):
                minio_client().make_bucket(bucket)
                print(f"[MinIO-OCR] Bucket créé : {bucket}")
            else:
                print(f"[MinIO-OCR] Bucket existant : {bucket}")
        except S3Error as e:
            print(f"[MinIO-OCR] Erreur bucket {bucket} : {e}")
    print(f"[MinIO-OCR] Stockage initialisé sur {MINIO_ENDPOINT}")


# ==============================================================================
# UPLOAD IMAGE SOURCE (remplace sauvegarder_image dans main.py)
# ==============================================================================

def sauvegarder_image_minio(upload, idx: int, session_id: str) -> Path:
    """
    Sauvegarde une image uploadée :
      1. Écrit temporairement sur disque local (nécessaire pour Pillow/cv2)
      2. Upload vers MinIO bucket 'uniburkina-ocr-uploads'
      3. Retourne le chemin LOCAL temporaire (utilisé par les fonctions OCR)

    Le chemin retourné est un Path local valide — toutes les fonctions OCR
    (ocr_image, extraire_layout_cv2, etc.) fonctionnent sans modification.
    """
    ext       = Path(upload.filename or "img.jpg").suffix or ".jpg"
    nom       = f"{session_id}_{idx:03d}{ext}"
    tmp_path  = _TMP_UPLOAD / nom

    # Écriture locale temporaire
    contenu = upload.file.read()
    with open(tmp_path, "wb") as f:
        f.write(contenu)
    upload.file.seek(0)

    # Upload MinIO (asynchrone en arrière-plan — ne bloque pas l'OCR)
    try:
        minio_client().put_object(
            BUCKET_UPLOADS,
            nom,
            io.BytesIO(contenu),
            len(contenu),
            content_type=upload.content_type or "image/jpeg",
        )
    except S3Error as e:
        # Non bloquant : l'OCR continue même si MinIO échoue sur l'upload source
        print(f"[MinIO-OCR] Avertissement upload image {nom} : {e}")

    return tmp_path


# ==============================================================================
# UPLOAD FICHIER GÉNÉRÉ (PDF, DOCX, XLSX, PPTX, TXT, MD)
# Appeler après generer_pdf(), generer_docx(), etc.
# ==============================================================================

def uploader_fichier_genere(chemin_local: Path, content_type: str = None) -> str:
    """
    Upload un fichier généré (PDF/DOCX/etc.) vers MinIO 'uniburkina-ocr-output'.
    Retourne la CLÉ MinIO (objet_key) — à stocker dans DocumentOCR.chemin_pdf.
    Le fichier local temporaire est supprimé après upload.
    """
    nom         = chemin_local.name
    ct          = content_type or _deviner_content_type(chemin_local)

    with open(chemin_local, "rb") as f:
        contenu = f.read()

    minio_client().put_object(
        BUCKET_OUTPUTS,
        nom,
        io.BytesIO(contenu),
        len(contenu),
        content_type=ct,
    )

    # Nettoyage fichier temporaire local
    try:
        chemin_local.unlink()
    except Exception:
        pass

    return nom   # clé MinIO = nom du fichier


# ==============================================================================
# TÉLÉCHARGEMENT FICHIER GÉNÉRÉ (pour endpoint /ocr/documents/{id}/telecharger)
# ==============================================================================

def telecharger_fichier_genere(objet_key: str) -> tuple[bytes, str]:
    """
    Télécharge un fichier généré depuis MinIO.
    Retourne (contenu_bytes, content_type).
    Lève FileNotFoundError si introuvable.
    """
    try:
        response = minio_client().get_object(BUCKET_OUTPUTS, objet_key)
        contenu  = response.read()
        ct       = response.headers.get("Content-Type", "application/octet-stream")
        return contenu, ct
    except S3Error as e:
        raise FileNotFoundError(f"Fichier OCR introuvable dans MinIO : {objet_key} — {e}")


# ==============================================================================
# URL PRÉSIGNÉE (optionnel — téléchargement direct frontend)
# ==============================================================================

def url_presignee_output(objet_key: str, expire_minutes: int = 60) -> str:
    """Génère une URL présignée pour téléchargement direct depuis MinIO."""
    return minio_client().presigned_get_object(
        BUCKET_OUTPUTS,
        objet_key,
        expires=timedelta(minutes=expire_minutes),
    )


# ==============================================================================
# EXISTENCE FICHIER GÉNÉRÉ
# ==============================================================================

def fichier_genere_existe(objet_key: str) -> bool:
    """Vérifie si un fichier généré existe dans MinIO."""
    if not objet_key:
        return False
    try:
        minio_client().stat_object(BUCKET_OUTPUTS, objet_key)
        return True
    except S3Error:
        return False


# ==============================================================================
# HELPERS INTERNES
# ==============================================================================

def _deviner_content_type(chemin: Path) -> str:
    ext = chemin.suffix.lower()
    mapping = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt":  "text/plain; charset=utf-8",
        ".md":   "text/markdown; charset=utf-8",
    }
    return mapping.get(ext, "application/octet-stream")


def get_tmp_output_dir() -> Path:
    """Retourne le dossier temporaire local pour la génération de fichiers."""
    return _TMP_OUTPUT


def get_tmp_upload_dir() -> Path:
    """Retourne le dossier temporaire local pour les images uploadées."""
    return _TMP_UPLOAD
