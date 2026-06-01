# UniBurkina Hub — Landing Page (GitHub Pages)

> **Version statique de démonstration** de la plateforme GED Académique UniBurkina Hub.  
> La plateforme complète (FastAPI + PostgreSQL + PaddleOCR) tourne en local à l'UTS.

---

## 🚀 Ce dépôt contient

| Fichier | Description |
|---|---|
| `index.html` | Landing page complète (design africain-moderne) |
| `manifest.json` | Manifeste PWA — installation sur mobile |
| `sw.js` | Service Worker — mode hors-ligne |
| `icons/` | Icônes PWA 192×512 px |

---

## 📦 Projet complet

**Repo principal** (à créer) : `uniburkina-hub`  
Contient les 6 microservices Python/FastAPI, les templates Jinja2, les scripts PowerShell.

---

## 🎓 Auteur

**AVOGAN Koudjo Augustin Sandaogo**  
INE N01213620231 — UTS, Université Thomas SANKARA  
Soutenance · Juillet 2026  
📧 avoganaugustin5@gmail.com

---

## 🛠️ Stack technique (plateforme complète)

- **Backend** : FastAPI 0.111 · 6 microservices · Python 3.11
- **OCR** : PaddleOCR 3.5.0 · streaming SSE · score de confiance
- **BDD** : PostgreSQL 5432 · SQLAlchemy 2.0 · 18+ tables
- **Recherche** : Elasticsearch 8.13.4
- **Auth** : JWT (python-jose) · bcrypt 4.0.1
- **Frontend** : FastAPI + Jinja2 · Bootstrap 5 · port 8000
