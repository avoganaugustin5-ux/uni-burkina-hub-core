import shutil
from pathlib import Path

MAIN = Path("main.py")
shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))

src = MAIN.read_text(encoding="utf-8")

# 1. Corriger le template etudiant_profil.html -> profil.html
src = src.replace('"etudiant_profil.html"', '"profil.html"')

# 2. Helper + routes profil pour tous les roles
NEW_ROUTES = '''

async def _profil_context(request: Request):
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

ANCHOR = '@app.get("/enseignant/dashboard", response_class=HTMLResponse)'
if ANCHOR in src:
    src = src.replace(ANCHOR, NEW_ROUTES + ANCHOR)
    print("OK routes inserees")
else:
    print("ERREUR ancre non trouvee")

MAIN.write_text(src, encoding="utf-8")
print("main.py patche")
