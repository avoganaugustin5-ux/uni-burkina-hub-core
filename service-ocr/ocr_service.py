# ==============================================================================
# service-ocr/ocr_service.py — UniBurkina Hub
# Remplace l'ancien ocr_service.py basé sur Tesseract.
# Ce fichier n'est plus le moteur principal (c'est main.py qui appelle
# PaddleOCR directement via ocr_image() et extraire_regions()).
# Il expose des helpers de validation et de sauvegarde réutilisables,
# et la fonction haute-niveau `traiter_image_complete` qui orchestre
# PaddleOCR → Groq Vision en un seul appel.
# ==============================================================================

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("service-ocr.service")

# ── Répertoire de sortie (cohérent avec main.py) ─────────────────────────────
OUTPUT_DIR = Path(os.getenv("OCR_TMP_DIR", "tmp_ocr")) / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Extensions acceptées
TYPES_AUTORISES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def valider_fichier_ocr(nom: str) -> tuple[bool, str]:
    """Valide l'extension d'un fichier image avant traitement OCR."""
    ext = Path(nom).suffix.lower()
    if ext not in TYPES_AUTORISES:
        return False, f"Type non autorisé : {ext}. Acceptés : {', '.join(sorted(TYPES_AUTORISES))}"
    return True, "OK"


async def traiter_image_complete(
    chemin: Path,
    ocr_image_fn,          # fonction ocr_image() de main.py
    extraire_regions_fn,   # fonction extraire_regions() de main.py
    nettoyer_fn,           # fonction _nettoyer_texte_ocr() de main.py
    score_fn,              # fonction _score_confiance() de main.py
    utiliser_groq: bool = True,
) -> dict:
    """
    Pipeline complet sur une image :
      1. PaddleOCR + layout OpenCV (via les fonctions de main.py)
      2. Optionnel : Groq Vision pour correction et amélioration

    Retourne :
        {
            "texte_extrait":  str,   # texte PaddleOCR brut nettoyé
            "texte_corrige":  str,   # texte après correction Groq (ou identique si Groq KO)
            "has_figures":    bool,
            "moteur":         str,   # "paddleocr" | "paddleocr+layout" | "paddleocr+groq"
            "score_confiance": int,
            "groq_succes":    bool,
        }
    """
    # ── Étape 1 : PaddleOCR ──────────────────────────────────────────────────
    texte_paddle = ""
    has_figures  = False
    moteur       = "paddleocr"

    try:
        layout = extraire_regions_fn(chemin)
        blocs  = layout["blocs"]
        has_figures  = any(b["type"] == "figure" for b in blocs)
        texte_paddle = "\n".join(b["texte"] for b in blocs if b["type"] == "texte")
        texte_paddle = nettoyer_fn(texte_paddle)
        moteur       = "paddleocr+layout" if has_figures else "paddleocr"
    except Exception as e:
        log.error(f"PaddleOCR échoué sur {chemin.name} : {e}")
        moteur = "echec"

    score = score_fn(texte_paddle, moteur, has_figures)

    # ── Étape 2 : Groq Vision (correction post-OCR) ───────────────────────────
    groq_succes   = False
    texte_corrige = texte_paddle

    if utiliser_groq and moteur != "echec":
        try:
            from ocr_engine import groq_vision_corriger, GROQ_AVAILABLE
            if GROQ_AVAILABLE:
                resultat_groq = await groq_vision_corriger(chemin, texte_paddle)
                if resultat_groq["succes"]:
                    texte_corrige = resultat_groq["texte_corrige"]
                    moteur        = resultat_groq["moteur"]
                    score         = min(100, score + resultat_groq["score_bonus"])
                    groq_succes   = True
                else:
                    log.warning(f"Groq non utilisé : {resultat_groq['erreur']}")
        except ImportError:
            log.warning("ocr_engine.py introuvable — Groq désactivé")
        except Exception as e:
            log.error(f"Groq exception inattendue : {e}")

    return {
        "texte_extrait":   texte_paddle,
        "texte_corrige":   texte_corrige,
        "has_figures":     has_figures,
        "moteur":          moteur,
        "score_confiance": score,
        "groq_succes":     groq_succes,
    }
