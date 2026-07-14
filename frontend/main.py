# ==============================================================================
# frontend/main.py — UniBurkina Hub — Version 3.0
# AVOGAN Koudjo Augustin Sandaogo — INE N01213620231
# Ajouts v3.0 (par rapport à v2.1) :
#   - /inscription-personnel     → inscription direction/personnel UTS
#   - /circuit-documentaire      → circuit documentaire multi-niveaux
#   - /president/dashboard       → dashboard Président (propre, plus de redirect)
#   - /vp/dashboard              → dashboard VP-EIP et VP-RCU
#   - /sg/dashboard              → dashboard Secrétaire Général
#   - /cabinet/dashboard         → dashboard Cabinet
#   - /directeur/dashboard       → dashboard Directeurs
#   - /employe-service/dashboard → dashboard Employés de service
#   - _role_to_url() étendu aux nouveaux rôles
#   - Profils ajoutés pour tous les nouveaux rôles
# ==============================================================================

from __future__ import annotations

import logging
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, Response as FastAPIResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

API_AUTH   = os.getenv("API_AUTH",   "http://localhost:8001")
API_GED    = os.getenv("API_GED",    "http://localhost:8002")
API_OCR    = os.getenv("API_OCR",    "http://localhost:8003")
API_SEARCH = os.getenv("API_SEARCH", "http://localhost:8004")
API_FORUM  = os.getenv("API_FORUM",  "http://localhost:8005")

app = FastAPI(title="UniBurkina Hub — Frontend", version="3.0.0")
templates = Jinja2Templates(directory="templates")

static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════
# HELPER — Vérifier le JWT via service-auth
# ══════════════════════════════════════════════════════════
async def get_current_user(request: Request) -> "dict | None":
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{API_AUTH}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════
# PAGES PUBLIQUES
# ══════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil publique — UniBurkina Hub Landing."""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/accueil", response_class=HTMLResponse)
async def accueil(request: Request):
    """Alias /accueil → landing publique."""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/a-propos", response_class=HTMLResponse)
async def a_propos(request: Request):
    """Page À propos du projet UniBurkina Hub."""
    return templates.TemplateResponse("a_propos.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return _redirect_by_role(user.get("role"))
    return RedirectResponse(url="/", status_code=302)


@app.get("/connexion", response_class=HTMLResponse)
async def connexion_page(request: Request):
    """Formulaire de connexion réel — accessible via le bouton 'Se connecter' de la landing."""
    user = await get_current_user(request)
    if user:
        return _redirect_by_role(user.get("role"))
    return templates.TemplateResponse("login.html", {
        "request": request,
        "api_base_url": API_AUTH
    })

@app.get("/inscription", response_class=HTMLResponse)
async def inscription_page(request: Request):
    univs, ufrs, filieres = [], [], []
    uts_univ = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_univs    = await client.get(f"{API_AUTH}/auth/universites")
            r_ufrs     = await client.get(f"{API_AUTH}/auth/ufrs")
            r_filieres = await client.get(f"{API_AUTH}/auth/filieres")
            if r_univs.status_code    == 200: univs    = r_univs.json()
            if r_ufrs.status_code     == 200: ufrs     = r_ufrs.json()
            if r_filieres.status_code == 200: filieres = r_filieres.json()
    except Exception:
        pass
    if isinstance(univs, list):
        uts_univ = next(
            (u for u in univs if "Thomas SANKARA" in (u.get("nom_univ") or "")),
            None
        )
    return templates.TemplateResponse("inscription.html", {
        "request":      request,
        "api_base_url": API_AUTH,
        "univs":        univs    if isinstance(univs, list)    else [],
        "ufrs":         ufrs     if isinstance(ufrs, list)     else [],
        "filieres":     filieres if isinstance(filieres, list) else [],
        "uts_univ_id":  uts_univ.get("id_univ", "")             if uts_univ else "",
        "uts_univ_nom": uts_univ.get("nom_univ", "Universite Thomas SANKARA") if uts_univ else "",
    })


# ══════════════════════════════════════════════════════════
# NOUVELLE ROUTE v3.0 — Inscription Personnel/Direction UTS
# ══════════════════════════════════════════════════════════
@app.get("/inscription-personnel", response_class=HTMLResponse)
async def inscription_personnel_page(request: Request):
    """Formulaire d'inscription pour le personnel et la direction de l'UTS."""
    return templates.TemplateResponse("inscription_personnel.html", {
        "request":      request,
        "api_base_url": API_AUTH,
    })


# ══════════════════════════════════════════════════════════
# GED Administrative — Recherche réservée à l'administration UTS
# ══════════════════════════════════════════════════════════
ROLES_ADMINISTRATION = {
    "PRESIDENT", "CABINET", "VP_EIP", "VP_RCU", "SG",
    "DIRECTEUR", "EMPLOYE", "ADMIN", "SOUS_ADMIN",
}

@app.get("/recherche-administrative", response_class=HTMLResponse)
async def recherche_administrative_page(request: Request):
    """Espace de recherche documentaire (PaddleOCR + Elasticsearch) réservé à l'administration UTS."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/connexion", status_code=302)
    if user.get("role") not in ROLES_ADMINISTRATION:
        return RedirectResponse("/acces-refuse", status_code=302)

    return templates.TemplateResponse("recherche_administrative.html", {
        "request":    request,
        "user":       user,
        "api_search": API_SEARCH,
    })


@app.get("/deconnexion")
async def deconnexion():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(
        key="token", path="/", samesite="lax", secure=False, httponly=True,
    )
    return response

@app.get("/acces-refuse", response_class=HTMLResponse)
async def acces_refuse(request: Request):
    try:
        return templates.TemplateResponse("acces_refuse.html", {"request": request})
    except Exception:
        return HTMLResponse("""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Accès refusé — UniBurkina Hub</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#F4F7FB;display:flex;align-items:center;
justify-content:center;min-height:100vh;flex-direction:column;gap:1rem;padding:2rem;}
.card{background:#fff;border:1px solid #CDD8E4;border-radius:14px;padding:2.5rem 3rem;
text-align:center;max-width:420px;box-shadow:0 4px 24px rgba(4,44,83,.08);}
h1{color:#D84315;font-size:1.4rem;font-weight:700;margin-bottom:.5rem;}
p{color:#5A7288;font-size:.9rem;line-height:1.6;margin-bottom:1.5rem;}
a{display:inline-block;background:#185FA5;color:#fff;padding:.55rem 1.4rem;
border-radius:8px;text-decoration:none;font-weight:600;font-size:.88rem;}
</style></head>
<body><div class="card"><div style="font-size:3rem">⛔</div>
<h1>Accès refusé</h1>
<p>Vous n'avez pas les droits nécessaires pour accéder à cette page.</p>
<a href="/login">← Retour à la connexion</a>
</div></body></html>""", status_code=403)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Erreur — UniBurkina Hub</title>
<style>
body{{font-family:'Segoe UI',sans-serif;background:#F4F7FB;display:flex;align-items:center;
justify-content:center;min-height:100vh;flex-direction:column;padding:2rem;}}
.card{{background:#fff;border:1px solid #CDD8E4;border-radius:14px;padding:2.5rem 3rem;
text-align:center;max-width:460px;box-shadow:0 4px 24px rgba(4,44,83,.08);}}
h1{{color:#185FA5;font-size:1.4rem;font-weight:700;margin-bottom:.5rem;}}
p{{color:#5A7288;font-size:.88rem;line-height:1.6;margin-bottom:1.5rem;}}
.code{{background:#F4F7FB;border:1px solid #CDD8E4;border-radius:6px;padding:.5rem .8rem;
font-family:monospace;font-size:.78rem;color:#D84315;margin-bottom:1.5rem;word-break:break-all;}}
a{{display:inline-block;background:#185FA5;color:#fff;padding:.55rem 1.4rem;
border-radius:8px;text-decoration:none;font-weight:600;font-size:.88rem;margin-right:.5rem;}}
</style></head>
<body><div class="card"><div style="font-size:3rem;margin-bottom:1rem">⚠️</div>
<h1>Erreur interne du serveur</h1>
<p>Vérifiez que tous les microservices sont démarrés.</p>
<div class="code">{str(exc)[:200]}</div>
<a href="/login">← Connexion</a>
<a href="/health" style="background:#1D9E75;">Health check</a>
</div></body></html>""", status_code=500)


# ══════════════════════════════════════════════════════════
# /set-token — Stocker le JWT dans un cookie HTTPOnly
# ══════════════════════════════════════════════════════════
class TokenIn(BaseModel):
    token: str
    role:  str

@app.post("/set-token")
async def set_token(data: TokenIn):
    redirect_url = _role_to_url(data.role)
    response = JSONResponse(content={"redirect_url": redirect_url})
    response.set_cookie(
        key="token", value=data.token,
        httponly=True, samesite="lax", secure=False,
        max_age=86400, path="/",
    )
    return response


def _role_to_url(role: str) -> str:
    return {
        # Rôles existants — inchangés
        "ADMIN":             "/admin/dashboard",
        "SOUS_ADMIN":        "/sous-admin/dashboard",
        "ENSEIGNANT":        "/enseignant/dashboard",
        "DELEGUE":           "/delegue/dashboard",
        "ETUDIANT":          "/etudiant/dashboard",
        "CHEF_DEPARTEMENT":  "/chef-dept/dashboard",
        # Nouveaux rôles v3.0
        "PRESIDENT":         "/president/dashboard",
        "VP_EIP":            "/vp/dashboard",
        "VP_RCU":            "/vp/dashboard",
        "SG": "/sg/dashboard",
        "CABINET":           "/cabinet/dashboard",
        "DIRECTEUR":         "/directeur/dashboard",
        "EMPLOYE":         "/employe-service/dashboard",
    }.get(role, "/etudiant/dashboard")


def _redirect_by_role(role: str):
    return RedirectResponse(_role_to_url(role), status_code=302)


# ══════════════════════════════════════════════════════════
# HELPER — Vrai comptage "service" (documents VALIDE des collègues du même poste)
# Croise service-auth (utilisateurs-meme-poste) et service-ged (documents filtrés par IDs)
# ══════════════════════════════════════════════════════════
async def _docs_du_service(client: httpx.AsyncClient, user: dict, headers: dict):
    """Retourne (docs_service, compte_service) : les documents VALIDE soumis par
    tous les collègues occupant le même poste_id (ou à défaut la même branche+role)
    que l'utilisateur courant."""
    docs_service, compte_service = [], 0
    user_id = user.get("id")
    if not user_id:
        return docs_service, compte_service
    try:
        r_collegues = await client.get(
            f"{API_AUTH}/auth/utilisateurs-meme-poste/{user_id}",
            headers=headers,
        )
        if r_collegues.status_code != 200:
            return docs_service, compte_service
        ids = r_collegues.json().get("ids", [])
        if not ids:
            return docs_service, compte_service

        r_docs = await client.get(
            f"{API_GED}/ged/documents",
            params={"statut": "VALIDE", "ids_soumis_par": ",".join(ids)},
            headers=headers,
        )
        if r_docs.status_code == 200:
            data = r_docs.json()
            if isinstance(data, list):
                docs_service = data
                compte_service = len(data)
    except Exception:
        pass
    return docs_service, compte_service


# ══════════════════════════════════════════════════════════
# DASHBOARDS EXISTANTS — inchangés
# ══════════════════════════════════════════════════════════

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") != "ADMIN":
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ged_stats, univs, users = {}, [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_stats = await client.get(f"{API_GED}/ged/stats", headers=headers)
            r_univs = await client.get(f"{API_AUTH}/auth/universites", headers=headers)
            r_users = await client.get(f"{API_AUTH}/auth/utilisateurs", headers=headers)
            if r_stats.status_code == 200: ged_stats = r_stats.json()
            if r_univs.status_code == 200: univs     = r_univs.json()
            if r_users.status_code == 200: users     = r_users.json()
    except Exception:
        pass

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "user": user,
        "token": request.cookies.get("token", ""),
        "ged_stats": ged_stats,
        "univs": univs if isinstance(univs, list) else [],
        "users": users if isinstance(users, list) else [],
        "api_auth": API_AUTH, "api_ged": API_GED, "api_search": API_SEARCH,
    })


@app.get("/etudiant/dashboard", response_class=HTMLResponse)
async def etudiant_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["ETUDIANT", "DELEGUE", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    docs, annonces, sujets = [], [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_docs   = await client.get(f"{API_GED}/ged/documents",
                                        params={"statut": "VALIDE", "limite": 100})
            r_ann    = await client.get(f"{API_GED}/ged/annonces")
            r_sujets = await client.get(f"{API_FORUM}/forum/sujets", params={"limite": 5})
            if r_docs.status_code   == 200: docs     = r_docs.json()
            if r_ann.status_code    == 200: annonces = r_ann.json()
            if r_sujets.status_code == 200: sujets   = r_sujets.json()
    except Exception:
        pass

    return templates.TemplateResponse("etudiant_dashboard.html", {
        "request": request, "user": user,
        "docs":     docs     if isinstance(docs, list)     else [],
        "annonces": annonces if isinstance(annonces, list) else [],
        "sujets":   sujets   if isinstance(sujets, list)   else [],
        "api_ged": API_GED, "api_forum": API_FORUM, "api_search": API_SEARCH,
    })


@app.get("/etudiant/profil", response_class=HTMLResponse)
async def etudiant_profil(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["ETUDIANT", "DELEGUE", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    docs_soumis = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_docs = await client.get(
                f"{API_GED}/ged/documents",
                params={"id_soumis_par": user.get("id"), "limite": 20},
                headers=headers
            )
            if r_docs.status_code == 200:
                docs_soumis = r_docs.json()
    except Exception:
        pass

    return templates.TemplateResponse("profil.html", {
        "request": request,
        "user": user,
        "docs_soumis": docs_soumis if isinstance(docs_soumis, list) else [],
        "api_auth": API_AUTH,
        "api_ged":  API_GED,
    })


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
                params={"id_soumis_par": user.get("id"), "limite": 20},
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
    if user.get("role") != "ADMIN":
        return RedirectResponse("/acces-refuse", status_code=302)
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


@app.get("/enseignant/dashboard", response_class=HTMLResponse)
async def enseignant_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["ENSEIGNANT", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    docs, stats = [], {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_docs  = await client.get(f"{API_GED}/ged/documents", params={"limite": 20})
            r_stats = await client.get(f"{API_GED}/ged/stats")
            if r_docs.status_code  == 200: docs  = r_docs.json()
            if r_stats.status_code == 200: stats = r_stats.json()
    except Exception:
        pass

    return templates.TemplateResponse("enseignant_dashboard.html", {
        "request": request, "user": user,
        "token": request.cookies.get("token", ""),
        "docs":  docs if isinstance(docs, list) else [],
        "stats": stats, "api_ged": API_GED, "api_ocr": API_OCR, "api_search": API_SEARCH,
    })


@app.get("/sous-admin/dashboard", response_class=HTMLResponse)
async def sous_admin_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["SOUS_ADMIN", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    docs, signalements, stats, plannings = [], [], {}, []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_docs  = await client.get(f"{API_GED}/ged/documents",
                                       params={"statut": "EN_ATTENTE", "limite": 20},
                                       headers=headers)
            r_sigs  = await client.get(f"{API_FORUM}/forum/signalements", headers=headers)
            r_stats = await client.get(f"{API_GED}/ged/stats", headers=headers)
            r_plan  = await client.get(f"{API_GED}/ged/plannings", headers=headers)
            if r_docs.status_code  == 200: docs         = r_docs.json()
            if r_sigs.status_code  == 200: signalements = r_sigs.json()
            if r_stats.status_code == 200: stats        = r_stats.json()
            if r_plan.status_code  == 200: plannings    = r_plan.json()
    except Exception:
        pass

    return templates.TemplateResponse("sous_admin_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "docs":         docs         if isinstance(docs, list)         else [],
        "signalements": signalements if isinstance(signalements, list) else [],
        "plannings":    plannings    if isinstance(plannings, list)    else [],
        "stats": stats,
        "api_ged": API_GED, "api_forum": API_FORUM, "api_ocr": API_OCR, "api_search": API_SEARCH,
    })


@app.get("/delegue/dashboard", response_class=HTMLResponse)
async def delegue_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ocr_stats, docs, annonces = {}, [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_ocr  = await client.get(f"{API_OCR}/ocr/stats", headers=headers)
            r_docs = await client.get(f"{API_GED}/ged/documents",
                                      params={"statut": "VALIDE", "limite": 100},
                                      headers=headers)
            r_ann  = await client.get(f"{API_GED}/ged/annonces", headers=headers)
            if r_ocr.status_code  == 200: ocr_stats = r_ocr.json()
            if r_docs.status_code == 200: docs      = r_docs.json()
            if r_ann.status_code  == 200: annonces  = r_ann.json()
    except Exception:
        pass

    return templates.TemplateResponse("delegue_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "ocr_stats": ocr_stats,
        "docs":      docs     if isinstance(docs, list)     else [],
        "annonces":  annonces if isinstance(annonces, list) else [],
        "api_ocr": API_OCR, "api_ged": API_GED, "api_forum": API_FORUM, "api_search": API_SEARCH,
    })


@app.get("/chef-dept/dashboard", response_class=HTMLResponse)
async def chef_dept_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["CHEF_DEPARTEMENT", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ged_stats, ocr_stats, forum_stats, docs_attente = {}, {}, {}, []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_ged   = await client.get(f"{API_GED}/ged/stats",    headers=headers)
            r_ocr   = await client.get(f"{API_OCR}/ocr/stats",    headers=headers)
            r_forum = await client.get(f"{API_FORUM}/forum/stats", headers=headers)
            r_att   = await client.get(f"{API_GED}/ged/documents",
                                       params={"statut": "EN_ATTENTE", "limite": 10},
                                       headers=headers)
            if r_ged.status_code   == 200: ged_stats    = r_ged.json()
            if r_ocr.status_code   == 200: ocr_stats    = r_ocr.json()
            if r_forum.status_code == 200: forum_stats  = r_forum.json()
            if r_att.status_code   == 200: docs_attente = r_att.json()

            # ── FIX — resoudre le nom de l'UFR geree a partir de id_ufr_gere ──
            # (chef_dept_dashboard.html attend USER.nom_ufr ; sans ceci le
            # template retombe toujours sur le placeholder generique)
            if user.get("id_ufr_gere"):
                r_ufrs = await client.get(f"{API_AUTH}/auth/ufrs", headers=headers)
                if r_ufrs.status_code == 200:
                    ufrs = r_ufrs.json()
                    if isinstance(ufrs, list):
                        ufr_match = next(
                            (u for u in ufrs if u.get("id_ufr") == user.get("id_ufr_gere")),
                            None,
                        )
                        if ufr_match:
                            user["nom_ufr"] = ufr_match.get("nom_ufr")
    except Exception:
        pass

    return templates.TemplateResponse("chef_dept_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "ged_stats": ged_stats, "ocr_stats": ocr_stats, "forum_stats": forum_stats,
        "docs_attente": docs_attente if isinstance(docs_attente, list) else [],
        "api_ged": API_GED, "api_ocr": API_OCR, "api_forum": API_FORUM, "api_search": API_SEARCH,
    })


# ══════════════════════════════════════════════════════════
# NOUVEAUX DASHBOARDS v3.0
# ══════════════════════════════════════════════════════════

@app.get("/president/dashboard", response_class=HTMLResponse)
async def president_dashboard(request: Request):
    """Dashboard Président — vue institutionnelle globale."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["PRESIDENT", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ged_stats, circuits_recus, annonces = {}, [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_stats   = await client.get(f"{API_GED}/ged/stats", headers=headers)
            r_circuits = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_ann     = await client.get(f"{API_GED}/ged/annonces", headers=headers)
            if r_stats.status_code    == 200: ged_stats      = r_stats.json()
            if r_circuits.status_code == 200: circuits_recus = r_circuits.json()
            if r_ann.status_code      == 200: annonces       = r_ann.json()
    except Exception:
        pass

    return templates.TemplateResponse("president_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "ged_stats":      ged_stats,
        "circuits_recus": circuits_recus if isinstance(circuits_recus, list) else [],
        "annonces":       annonces       if isinstance(annonces, list)       else [],
        "api_ged": API_GED, "api_auth": API_AUTH,
    })


@app.get("/vp/dashboard", response_class=HTMLResponse)
async def vp_dashboard(request: Request):
    """Dashboard Vice-Présidents (VP-EIP et VP-RCU)."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["VP_EIP", "VP_RCU", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ged_stats, circuits_recus, circuits_envoyes = {}, [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_stats    = await client.get(f"{API_GED}/ged/stats", headers=headers)
            r_recus    = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_envoyes  = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            if r_stats.status_code   == 200: ged_stats        = r_stats.json()
            if r_recus.status_code   == 200: circuits_recus   = r_recus.json()
            if r_envoyes.status_code == 200: circuits_envoyes = r_envoyes.json()
    except Exception:
        pass

    return templates.TemplateResponse("vp_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "ged_stats":        ged_stats,
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "api_ged": API_GED, "api_auth": API_AUTH,
    })


@app.get("/sg/dashboard", response_class=HTMLResponse)
async def sg_dashboard(request: Request):
    """Dashboard Secrétaire Général."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["SG", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    ged_stats, circuits_recus, circuits_envoyes, plannings = {}, [], [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_stats    = await client.get(f"{API_GED}/ged/stats", headers=headers)
            r_circuits = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_envoyes  = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            r_plan     = await client.get(f"{API_GED}/ged/plannings", headers=headers)
            if r_stats.status_code    == 200: ged_stats        = r_stats.json()
            if r_circuits.status_code == 200: circuits_recus   = r_circuits.json()
            if r_envoyes.status_code  == 200: circuits_envoyes = r_envoyes.json()
            if r_plan.status_code     == 200: plannings        = r_plan.json()
    except Exception:
        pass

    return templates.TemplateResponse("sg_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "ged_stats":        ged_stats,
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "plannings":        plannings        if isinstance(plannings, list)        else [],
        "api_ged": API_GED, "api_auth": API_AUTH,
    })


@app.get("/cabinet/dashboard", response_class=HTMLResponse)
async def cabinet_dashboard(request: Request):
    """Dashboard Cabinet (CCAB, CJ, SP, SC, CAT et services rattachés)."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["CABINET", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    circuits_recus, circuits_envoyes, annonces = [], [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_recus   = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_envoyes = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            r_ann     = await client.get(f"{API_GED}/ged/annonces", headers=headers)
            if r_recus.status_code   == 200: circuits_recus   = r_recus.json()
            if r_envoyes.status_code == 200: circuits_envoyes = r_envoyes.json()
            if r_ann.status_code     == 200: annonces         = r_ann.json()
    except Exception:
        pass

    return templates.TemplateResponse("cabinet_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "annonces":         annonces         if isinstance(annonces, list)         else [],
        "api_ged": API_GED, "api_auth": API_AUTH,
    })


@app.get("/directeur/dashboard", response_class=HTMLResponse)
async def directeur_dashboard(request: Request):
    """Dashboard Directeurs (DSI, DAF, DRH, DEI, DPE, DAOI, DRV, DCPE, DPRUE, DEP, BCMP, BUC)."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["DIRECTEUR", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    circuits_recus, circuits_envoyes = [], []
    docs_service, compte_service = [], 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_recus    = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_envoyes  = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            if r_recus.status_code   == 200: circuits_recus   = r_recus.json()
            if r_envoyes.status_code == 200: circuits_envoyes = r_envoyes.json()
            docs_service, compte_service = await _docs_du_service(client, user, headers)
    except Exception:
        pass

    return templates.TemplateResponse("directeur_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "docs_service":     docs_service     if isinstance(docs_service, list)     else [],
        "compte_service":   compte_service,
        "api_ged": API_GED, "api_auth": API_AUTH, "api_ocr": API_OCR,
    })


@app.get("/employe-service/dashboard", response_class=HTMLResponse)
async def employe_service_dashboard(request: Request):
    """Dashboard Employés de service (SSM, SRSS, SEAP, SAF, SCP, etc.)."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["EMPLOYE", "CABINET", "ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    circuits_recus, circuits_envoyes, annonces = [], [], []
    docs_service, compte_service = [], 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_recus   = await client.get(f"{API_GED}/ged/circuits/recus", headers=headers)
            r_envoyes = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            r_ann     = await client.get(f"{API_GED}/ged/annonces", headers=headers)
            if r_recus.status_code   == 200: circuits_recus   = r_recus.json()
            if r_envoyes.status_code == 200: circuits_envoyes = r_envoyes.json()
            if r_ann.status_code     == 200: annonces         = r_ann.json()
            docs_service, compte_service = await _docs_du_service(client, user, headers)
    except Exception:
        pass

    return templates.TemplateResponse("employe_service_dashboard.html", {
        "request": request, "user": user,
        "token": token or "",
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "annonces":         annonces         if isinstance(annonces, list)         else [],
        "docs_service":     docs_service     if isinstance(docs_service, list)     else [],
        "compte_service":   compte_service,
        "api_ged": API_GED, "api_auth": API_AUTH,
    })


# Profils pour les nouveaux rôles — tous utilisent le même template profil.html
@app.get("/president/profil", response_class=HTMLResponse)
async def president_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})

@app.get("/vp/profil", response_class=HTMLResponse)
async def vp_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})

@app.get("/sg/profil", response_class=HTMLResponse)
async def sg_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})

@app.get("/cabinet/profil", response_class=HTMLResponse)
async def cabinet_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})

@app.get("/directeur/profil", response_class=HTMLResponse)
async def directeur_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})

@app.get("/employe-service/profil", response_class=HTMLResponse)
async def employe_service_profil(request: Request):
    user, ctx = await _profil_context(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("profil.html", {"request": request, **ctx})


# ══════════════════════════════════════════════════════════
# MODULES EXISTANTS v2.1 — OCR Studio & Validation Hub
# ══════════════════════════════════════════════════════════

@app.get("/ocr-studio", response_class=HTMLResponse)
async def ocr_studio(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    filieres, modules, ocr_stats = [], [], {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_fil  = await client.get(f"{API_AUTH}/auth/filieres", headers=headers)
            r_mod  = await client.get(f"{API_AUTH}/auth/modules",  headers=headers)
            r_stat = await client.get(f"{API_OCR}/ocr/stats",      headers=headers)
            if r_fil.status_code  == 200: filieres  = r_fil.json()
            if r_mod.status_code  == 200: modules   = r_mod.json()
            if r_stat.status_code == 200: ocr_stats = r_stat.json()
    except Exception:
        pass

    role = user.get("role", "ETUDIANT")
    depot_direct_autorise = role in {"ADMIN", "SOUS_ADMIN", "CHEF_DEPARTEMENT"}

    return templates.TemplateResponse("ocr_studio.html", {
        "request": request,
        "user": user,
        "token": token or "",
        "filieres": filieres if isinstance(filieres, list) else [],
        "modules":  modules  if isinstance(modules, list)  else [],
        "ocr_stats": ocr_stats,
        "depot_direct_autorise": depot_direct_autorise,
        "api_ocr":  API_OCR,
        "api_ged":  API_GED,
        "api_auth": API_AUTH,
    })


@app.get("/validation-hub", response_class=HTMLResponse)
async def validation_hub(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["SOUS_ADMIN", "CHEF_DEPARTEMENT", "ADMIN", "PRESIDENT"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    docs_attente, docs_valides, docs_refuses, signalements, filieres = [], [], [], [], []
    stats_ged = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_att  = await client.get(f"{API_GED}/ged/documents",
                                      params={"statut": "EN_ATTENTE", "limite": 50},
                                      headers=headers)
            r_val  = await client.get(f"{API_GED}/ged/documents",
                                      params={"statut": "VALIDE",     "limite": 20},
                                      headers=headers)
            r_ref  = await client.get(f"{API_GED}/ged/documents",
                                      params={"statut": "REFUSE",     "limite": 20},
                                      headers=headers)
            r_sigs = await client.get(f"{API_FORUM}/forum/signalements", headers=headers)
            r_fil  = await client.get(f"{API_AUTH}/auth/filieres",       headers=headers)
            r_stat = await client.get(f"{API_GED}/ged/stats",            headers=headers)
            if r_att.status_code  == 200: docs_attente  = r_att.json()
            if r_val.status_code  == 200: docs_valides  = r_val.json()
            if r_ref.status_code  == 200: docs_refuses  = r_ref.json()
            if r_sigs.status_code == 200: signalements  = r_sigs.json()
            if r_fil.status_code  == 200: filieres      = r_fil.json()
            if r_stat.status_code == 200: stats_ged     = r_stat.json()
    except Exception:
        pass

    return templates.TemplateResponse("validation_hub.html", {
        "request": request,
        "user": user,
        "token": token or "",
        "docs_attente":  docs_attente  if isinstance(docs_attente, list)  else [],
        "docs_valides":  docs_valides  if isinstance(docs_valides, list)  else [],
        "docs_refuses":  docs_refuses  if isinstance(docs_refuses, list)  else [],
        "signalements":  signalements  if isinstance(signalements, list)  else [],
        "filieres":      filieres      if isinstance(filieres, list)      else [],
        "stats_ged":     stats_ged,
        "api_ged":    API_GED,
        "api_forum":  API_FORUM,
        "api_auth":   API_AUTH,
        "api_ocr":    API_OCR,
    })


# ══════════════════════════════════════════════════════════
# NOUVELLE ROUTE v3.0 — Circuit Documentaire
# ══════════════════════════════════════════════════════════
@app.get("/circuit-documentaire", response_class=HTMLResponse)
async def circuit_documentaire(request: Request):
    """Circuit documentaire multi-niveaux — accessible à tous les rôles connectés."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    token = request.cookies.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    circuits_envoyes, circuits_recus = [], []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r_env = await client.get(f"{API_GED}/ged/circuits/mes-documents", headers=headers)
            r_rec = await client.get(f"{API_GED}/ged/circuits/recus",         headers=headers)
            if r_env.status_code == 200: circuits_envoyes = r_env.json()
            if r_rec.status_code == 200: circuits_recus   = r_rec.json()
    except Exception:
        pass

    return templates.TemplateResponse("circuit_documentaire.html", {
        "request": request,
        "user": user,
        "token": token or "",
        "circuits_envoyes": circuits_envoyes if isinstance(circuits_envoyes, list) else [],
        "circuits_recus":   circuits_recus   if isinstance(circuits_recus, list)   else [],
        "api_ged":  API_GED,
        "api_auth": API_AUTH,
    })


# ══════════════════════════════════════════════════════════
# ADMINISTRATION — GROUPES DE SERVICE (cloisonnement documentaire)
# Reservee a ADMIN / SOUS_ADMIN, en miroir exact de la protection deja
# appliquee cote service-auth (require_admin_or_sous_admin) sur les
# endpoints /auth/groupes-service*. Toutes les donnees sont chargees et
# modifiees cote client via le proxy generique /api/auth/{path} deja
# existant (injecte automatiquement le token depuis le cookie) — cette
# route ne fait donc que servir la page, sans nouvel appel serveur.
# ══════════════════════════════════════════════════════════
@app.get("/admin/groupes-service", response_class=HTMLResponse)
async def admin_groupes_service(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.get("role") not in ["ADMIN", "SOUS_ADMIN"]:
        return RedirectResponse("/acces-refuse", status_code=302)

    return templates.TemplateResponse("groupes_service_admin.html", {
        "request": request,
        "user": user,
        "token": request.cookies.get("token", ""),
        "api_auth": API_AUTH,
    })


# ══════════════════════════════════════════════════════════
# PROXY TÉLÉCHARGEMENT OCR
# ══════════════════════════════════════════════════════════
@app.get("/ocr/proxy-telecharger/{id_ocr}")
async def proxy_telecharger_ocr(id_ocr: int, request: Request):
    """Proxy sécurisé : transfère le cookie JWT vers service-ocr pour téléchargement."""
    token = request.cookies.get("token")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{API_OCR}/ocr/documents/{id_ocr}/telecharger",
                headers={"Authorization": f"Bearer {token}"} if token else {}
            )
        if r.status_code == 200:
            return StreamingResponse(
                iter([r.content]),
                media_type=r.headers.get("content-type", "application/octet-stream"),
                headers={"Content-Disposition": r.headers.get("content-disposition", "attachment")}
            )
    except Exception:
        pass
    return JSONResponse({"detail": "Fichier introuvable"}, status_code=404)


# ══════════════════════════════════════════════════════════
# PROXY UNIVERSEL
# ══════════════════════════════════════════════════════════

async def _proxy(request: Request, target_url: str) -> FastAPIResponse:
    token = request.cookies.get("token")
    content_type = request.headers.get("content-type", "")

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding",
                              "connection", "keep-alive")
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    _ocr_heavy = (
        "/ocr/scan", "/ocr/scan-multi", "/ocr/retranscrire",
        "/ocr/retranscrire-stream", "/ocr/generer-document",
        "/ocr/generer-direct", "/ocr/soumettre-direct",
        "/ocr/soumettre-ged", "/ocr/generer", "/ocr/scan-et-ged",
    )
    if any(seg in target_url for seg in _ocr_heavy):
        _timeout = httpx.Timeout(connect=10.0, write=300.0, read=900.0, pool=10.0)
    else:
        _timeout = httpx.Timeout(connect=10.0, write=30.0, read=120.0, pool=10.0)

    try:
        async with httpx.AsyncClient(timeout=_timeout) as client:

            if "multipart/form-data" in content_type:
                form = await request.form()
                files_to_send = []
                data_to_send  = {}

                for key, value in form.multi_items():
                    if hasattr(value, "read"):
                        content = await value.read()
                        files_to_send.append(
                            (key, (value.filename, content, value.content_type or "application/octet-stream"))
                        )
                    else:
                        if key in data_to_send:
                            existing = data_to_send[key]
                            if isinstance(existing, list):
                                existing.append(value)
                            else:
                                data_to_send[key] = [existing, value]
                        else:
                            data_to_send[key] = value

                headers.pop("content-type", None)

                r = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    files=files_to_send if files_to_send else None,
                    data=data_to_send   if data_to_send  else None,
                    params=dict(request.query_params),
                    follow_redirects=True,
                )
            else:
                body = await request.body()
                r = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body if body else None,
                    params=dict(request.query_params),
                    follow_redirects=True,
                )

        resp_headers = {
            k: v for k, v in r.headers.items()
            if k.lower() not in ("transfer-encoding", "content-encoding",
                                  "content-length", "connection")
        }
        return FastAPIResponse(
            content=r.content,
            status_code=r.status_code,
            headers=resp_headers,
            media_type=r.headers.get("content-type"),
        )

    except httpx.ConnectError as e:
        logging.getLogger("frontend-proxy").error(f"ConnectError vers {target_url}: {e}")
        service_name = (
            "service-ocr (port 8003)"  if ":8003" in target_url else
            "service-ged (port 8002)"  if ":8002" in target_url else
            "service-auth (port 8001)" if ":8001" in target_url else
            "microservice"
        )
        return FastAPIResponse(
            content=(
                '{"detail":"' + service_name + ' inaccessible — '
                'verifiez qu il est demarre"}'
            ).encode(),
            status_code=503,
            media_type="application/json",
        )
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
        logging.getLogger("frontend-proxy").warning(
            f"Timeout ({type(e).__name__}) vers {target_url}"
        )
        is_ocr_gen = "/ocr/generer" in target_url
        msg = (
            "Generation trop longue — service-ocr encore en initialisation (PaddleOCR). "
            "Attendez 30 secondes et reessayez."
            if is_ocr_gen else
            "Le traitement prend trop de temps. Essayez avec moins de fichiers."
        )
        return FastAPIResponse(
            content=('{"detail":"' + msg + '"}'). encode(),
            status_code=504,
            media_type="application/json",
        )
    except Exception as e:
        logging.getLogger("frontend-proxy").error(f"Proxy exception vers {target_url}: {e}", exc_info=True)
        err_msg = str(e).replace('"', "'")
        err_body = ('{"detail":"Erreur proxy: ' + err_msg + '"}').encode()
        return FastAPIResponse(
            content=err_body,
            status_code=502,
            media_type="application/json",
        )


# ── Proxy SSE dédié : retranscrire-stream ──────────────────
@app.post("/api/ocr/retranscrire-stream")
async def proxy_ocr_sse_stream(request: Request):
    """Proxy SSE transparent pour /ocr/retranscrire-stream — stream chunk par chunk."""
    token = request.cookies.get("token")
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding",
                              "connection", "keep-alive")
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    content_type = request.headers.get("content-type", "")
    files_to_send = []
    data_to_send  = {}

    if "multipart/form-data" in content_type:
        form = await request.form()
        for key, value in form.multi_items():
            if hasattr(value, "read"):
                file_content = await value.read()
                files_to_send.append(
                    (key, (value.filename, file_content, value.content_type or "application/octet-stream"))
                )
            else:
                if key in data_to_send:
                    existing = data_to_send[key]
                    data_to_send[key] = existing if isinstance(existing, list) else [existing]
                    data_to_send[key].append(value)
                else:
                    data_to_send[key] = value
        headers.pop("content-type", None)

    target_url = f"{API_OCR}/ocr/retranscrire-stream"

    async def event_generator():
        timeout = httpx.Timeout(connect=10.0, write=120.0, read=None, pool=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    method="POST",
                    url=target_url,
                    headers=headers,
                    files=files_to_send if files_to_send else None,
                    data=data_to_send   if data_to_send  else None,
                    params=dict(request.query_params),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except Exception as e:
            logging.getLogger("frontend-proxy").error(f"SSE stream error: {e}")
            yield f"event: error\ndata: {str(e)}\n\n".encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@app.api_route("/api/ocr/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_ocr(path: str, request: Request):
    return await _proxy(request, f"{API_OCR}/ocr/{path}")

@app.api_route("/api/ged/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_ged(path: str, request: Request):
    return await _proxy(request, f"{API_GED}/ged/{path}")

@app.get("/api/auth/filieres")
async def proxy_auth_filieres(request: Request):
    token = request.cookies.get("token")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{API_AUTH}/auth/filieres", headers=headers)
        if r.status_code == 200:
            return JSONResponse(content=r.json(), status_code=200)
        return JSONResponse(content=[], status_code=200)
    except Exception:
        return JSONResponse(content=[], status_code=200)

@app.get("/api/auth/journal-audit")
async def proxy_auth_journal_audit(request: Request):
    token = request.cookies.get("token")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{API_AUTH}/auth/journal-audit",
                headers=headers,
                params=dict(request.query_params),
                follow_redirects=True,
            )
        if r.status_code == 200:
            return JSONResponse(content=r.json(), status_code=200)
        return JSONResponse(content=[], status_code=200)
    except Exception:
        return JSONResponse(content=[], status_code=200)

@app.api_route("/api/auth/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_auth(path: str, request: Request):
    return await _proxy(request, f"{API_AUTH}/auth/{path}")

@app.api_route("/api/forum/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_forum(path: str, request: Request):
    return await _proxy(request, f"{API_FORUM}/forum/{path}")

@app.api_route("/api/search/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_search(path: str, request: Request):
    return await _proxy(request, f"{API_SEARCH}/search/{path}")


# ══════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════

@app.get("/get-token", tags=["Système"])
async def get_token(request: Request):
    token = request.cookies.get("token")
    if not token:
        return JSONResponse({"token": None}, status_code=200)
    return JSONResponse({"token": token})

@app.get("/health")
def health():
    return {
        "status":  "ok",
        "service": "uniburkina-frontend",
        "version": "3.0.0",
        "routes_nouvelles": [
            "/inscription-personnel",
            "/circuit-documentaire",
            "/president/dashboard",
            "/vp/dashboard",
            "/sg/dashboard",
            "/cabinet/dashboard",
            "/directeur/dashboard",
            "/employe-service/dashboard",
        ]
    }
