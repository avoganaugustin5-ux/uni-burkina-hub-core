# ==============================================================================
# service-ocr/ocr_engine.py — UniBurkina Hub
# Moteur Groq Vision (llama-4-scout-17b-16e-instruct) — Gratuit, rapide
# Rôle : amélioration post-OCR PaddleOCR via vision LLM
#   - Reçoit l'image brute + le texte PaddleOCR déjà extrait
#   - Groq corrige les erreurs OCR, lit les formules, améliore la structure
#   - Retourne texte corrigé + score de confiance amélioré
# ==============================================================================

import os
import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("service-ocr.engine")

# ── Config Groq ───────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "meta-llama/llama-4-scout-17b-16e-instruct"  # Vision + gratuit
GROQ_TIMEOUT   = 30.0   # secondes — Groq est très rapide (<3s habituellement)
GROQ_MAX_TOKENS = 4096

GROQ_AVAILABLE = bool(GROQ_API_KEY)


def _encoder_image_base64(chemin: Path) -> tuple[str, str]:
    """Encode une image en base64 et détecte son type MIME."""
    ext = chemin.suffix.lower()
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".bmp":  "image/bmp",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif":  "image/tiff",
    }
    mime = mime_map.get(ext, "image/jpeg")
    data = base64.b64encode(chemin.read_bytes()).decode("utf-8")
    return data, mime


def _construire_prompt(texte_paddle: str) -> str:
    """
    Construit le prompt système pour Groq Vision.
    On passe le texte PaddleOCR déjà extrait pour que Groq l'améliore,
    plutôt que de tout re-extraire (économise des tokens, va plus vite).
    """
    return f"""Tu es un assistant de correction OCR pour des documents académiques universitaires burkinabè.

On t'envoie une image de devoir/cours et le texte déjà extrait automatiquement par PaddleOCR.

Texte PaddleOCR (peut contenir des erreurs) :
---
{texte_paddle if texte_paddle.strip() else "(aucun texte extrait — image possiblement illisible ou contient uniquement des formules/figures)"}
---

Ta mission :
1. Corriger les erreurs de reconnaissance (lettres confondues, mots coupés, accents manquants)
2. Reconnaître et retranscrire les formules mathématiques en notation lisible (ex: "x² + 2x = 0", "∑ i=1 à n")
3. Préserver la structure du document (titres, numérotation, paragraphes)
4. Si le texte PaddleOCR est vide mais que l'image contient du texte, l'extraire toi-même
5. Ne pas inventer de contenu — corriger uniquement, pas compléter

Réponds UNIQUEMENT avec le texte corrigé, sans commentaire, sans balise, sans explication."""


async def groq_vision_corriger(
    chemin: Path,
    texte_paddle: str,
) -> dict:
    """
    Envoie l'image + texte PaddleOCR à Groq Vision pour correction.

    Retourne :
        {
            "succes": bool,
            "texte_corrige": str,
            "moteur": "paddleocr+groq" | "paddleocr",
            "score_bonus": int,   # bonus de score à ajouter (+15 si succès)
            "erreur": str | None
        }
    """
    if not GROQ_AVAILABLE:
        log.warning("GROQ_API_KEY non configurée — correction Groq désactivée.")
        return {
            "succes": False,
            "texte_corrige": texte_paddle,
            "moteur": "paddleocr",
            "score_bonus": 0,
            "erreur": "GROQ_API_KEY non configurée",
        }

    try:
        b64, mime = _encoder_image_base64(chemin)
        prompt    = _construire_prompt(texte_paddle)

        payload = {
            "model": GROQ_MODEL,
            "max_tokens": GROQ_MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=GROQ_TIMEOUT) as client:
            r = await client.post(
                GROQ_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
            )

        if r.status_code != 200:
            log.warning(f"Groq API erreur {r.status_code} : {r.text[:300]}")
            return {
                "succes": False,
                "texte_corrige": texte_paddle,
                "moteur": "paddleocr",
                "score_bonus": 0,
                "erreur": f"Groq HTTP {r.status_code}",
            }

        data   = r.json()
        texte  = data["choices"][0]["message"]["content"].strip()
        tokens = data.get("usage", {}).get("total_tokens", 0)
        log.info(f"Groq Vision OK — {tokens} tokens, {len(texte)} chars retournés")

        return {
            "succes": True,
            "texte_corrige": texte,
            "moteur": "paddleocr+groq",
            "score_bonus": 15,   # bonus confiance : Groq a validé/corrigé le texte
            "erreur": None,
        }

    except httpx.TimeoutException:
        log.warning(f"Groq Vision timeout ({GROQ_TIMEOUT}s) — on garde le texte PaddleOCR")
        return {
            "succes": False,
            "texte_corrige": texte_paddle,
            "moteur": "paddleocr",
            "score_bonus": 0,
            "erreur": "Timeout Groq",
        }
    except Exception as e:
        log.error(f"Groq Vision exception : {e}")
        return {
            "succes": False,
            "texte_corrige": texte_paddle,
            "moteur": "paddleocr",
            "score_bonus": 0,
            "erreur": str(e),
        }
