"""
Patch frontend/main.py :
  1. Corriger /etudiant/profil → profil.html (au lieu de etudiant_profil.html)
  2. Ajouter les routes /enseignant/profil, /admin/profil, /sous-admin/profil,
     /delegue/profil, /chef-dept/profil — toutes pointent vers profil.html
     avec les mêmes variables que /etudiant/profil.

Utilisation :
  cd C:\projets\UniBurkina_Hub\frontend
  python patch_profil_routes.py
"""

import re, shutil
from pathlib import Path

MAIN = Path("main.py")
assert MAIN.exists(), "Lancer ce script depuis le dossier frontend/"

# Sauvegarde
shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))
print("Sauvegarde → main.py.bak")

src = MAIN.read_text(encoding="utf-8")

# ── 1. Corriger etudiant_profil.html → profil.html ────────────────────
src = src.replace('"etudiant_profil.html"', '"profil.html"')
print("✓ /etudiant/profil → profil.html")

# ── 2. Insérer les nouvelles routes juste après la route etudiant/profil ──
ANCHOR = '''@app.get("/enseignant/dashboard", response_class=HTMLResponse)'''

NEW_ROUTES = '''
# ══════════════════════════════════════════════════════════
# ROUTES PROFIL — tous rôles → profil.html (template unique)
# ══════════════════════════════════════════════════════════

async def _profil_context(request: Request):
    """Helper commun : récupère user + docs soumis pour la page profil."""
    user = await get_current_user(request)
    if not user:
        return None, None
    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    docs_soumis = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{API_GED}/ged/documents",
                params={"id_soumis_par": user.get("id_utilisateur"), "limite": 20},
                headers=headers
            )
            if r.status_code == 200:
                docs_soumis = r.json()
    except Exception:
        pass
    ctx = {
        "user": user,
        "docs_soumis": docs_soumis if isinstance(docs_soumis, list) else [],
        "api_auth": API_AUTH,
        "api_ged":  API_GED,
    }
    return user, ctx


@app.get("/enseignant/profil", response_class=HTMLResponse)
async def enseignant_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


@app.get("/admin/profil", response_class=HTMLResponse)
async def admin_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


@app.get("/sous-admin/profil", response_class=HTMLResponse)
async def sous_admin_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


@app.get("/delegue/profil", response_class=HTMLResponse)
async def delegue_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


@app.get("/chef-dept/profil", response_class=HTMLResponse)
async def chef_dept_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


'''

if ANCHOR in src:
    src = src.replace(ANCHOR, NEW_ROUTES + ANCHOR)
    print("✓ Routes /*/profil insérées (enseignant, admin, sous-admin, délégué, chef-dept)")
else:
    print("⚠️  Ancre non trouvée — ajout en fin de fichier")
    src += "\n" + NEW_ROUTES

MAIN.write_text(src, encoding="utf-8")
print("\n✅  main.py patché avec succès.")
print("   Uvicorn avec --reload va recharger automatiquement.")
