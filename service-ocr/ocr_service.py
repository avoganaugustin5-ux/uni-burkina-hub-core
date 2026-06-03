import pytesseract
from PIL import Image
from pathlib import Path
from datetime import datetime
import uuid, os

# ── Chemin Tesseract (adapter si different) ────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OUTPUT_DIR = Path(os.getenv("LOCAL_STORAGE_PATH", "C:/projets/UniBurkina_Hub/storage")) / "ocr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TYPES_AUTORISES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".pdf"}

def valider_fichier_ocr(nom: str) -> tuple[bool, str]:
    ext = Path(nom).suffix.lower()
    if ext not in TYPES_AUTORISES:
        return False, f"Type non autorise : {ext}"
    return True, "OK"

def extraire_texte(chemin_image: str, langue: str = "fra") -> dict:
    """Extrait le texte d'une image via Tesseract."""
    try:
        img = Image.open(chemin_image)
        texte = pytesseract.image_to_string(img, lang=langue)
        return {"succes": True, "texte": texte.strip(), "erreur": None}
    except Exception as e:
        return {"succes": False, "texte": None, "erreur": str(e)}

def generer_pdf_depuis_texte(texte: str, nom_base: str) -> str:
    """Génère un PDF à partir du texte extrait via ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    nom_pdf = OUTPUT_DIR / f"{uuid.uuid4().hex}_{nom_base}.pdf"
    doc = SimpleDocTemplate(str(nom_pdf), pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(f"Document numerise — {nom_base}", styles["Title"]))
    story.append(Spacer(1, 12))

    for ligne in texte.split("\n"):
        ligne = ligne.strip()
        if ligne:
            story.append(Paragraph(ligne, styles["Normal"]))
            story.append(Spacer(1, 4))

    doc.build(story)
    return str(nom_pdf)

def sauvegarder_fichier(contenu: bytes, nom_original: str) -> str:
    """Sauvegarde le fichier uploadé sur disque."""
    ext = Path(nom_original).suffix.lower()
    nom_unique = f"{uuid.uuid4().hex}{ext}"
    chemin = OUTPUT_DIR / nom_unique
    with open(chemin, "wb") as f:
        f.write(contenu)
    return str(chemin)