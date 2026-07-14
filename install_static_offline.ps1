# ==============================================================================
# install_static_offline.ps1 — UniBurkina Hub
# Télécharge Bootstrap + Tabler Icons en local et patche ocr_studio.html
# Lancer depuis : C:\projets\UniBurkina_Hub\
# ==============================================================================

$ErrorActionPreference = "Stop"
$BASE = "C:\projets\UniBurkina_Hub"

Write-Host "`n[UniBurkina] Mise en mode offline des assets statiques..." -ForegroundColor Cyan

# ── 1. Créer les dossiers static ──────────────────────────────────────────────
$cssDir   = "$BASE\frontend\static\css"
$fontsDir = "$BASE\frontend\static\fonts"
New-Item -ItemType Directory -Force -Path $cssDir   | Out-Null
New-Item -ItemType Directory -Force -Path $fontsDir | Out-Null
Write-Host "[1/6] Dossiers static créés" -ForegroundColor Green

# ── 2. Télécharger Bootstrap CSS ──────────────────────────────────────────────
$bootstrapUrl = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
$bootstrapOut = "$cssDir\bootstrap.min.css"
Invoke-WebRequest -Uri $bootstrapUrl -OutFile $bootstrapOut -UseBasicParsing
Write-Host "[2/6] Bootstrap CSS téléchargé ($(([System.IO.FileInfo]$bootstrapOut).Length / 1KB -as [int]) Ko)" -ForegroundColor Green

# ── 3. Télécharger Tabler Icons CSS ──────────────────────────────────────────
$tablerCssUrl = "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.5.0/tabler-icons.min.css"
$tablerCssOut = "$cssDir\tabler-icons.min.css"
Invoke-WebRequest -Uri $tablerCssUrl -OutFile $tablerCssOut -UseBasicParsing
Write-Host "[3/6] Tabler Icons CSS téléchargé" -ForegroundColor Green

# ── 4. Télécharger les polices Tabler (woff2) ─────────────────────────────────
# Lire le CSS pour extraire les URLs de polices
$tablerCssContent = Get-Content $tablerCssOut -Raw
$fontUrls = [regex]::Matches($tablerCssContent, "url\('(https://[^']+\.woff2)[^']*'\)") |
            ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique

if ($fontUrls) {
    foreach ($url in $fontUrls) {
        $fontFile = Split-Path $url -Leaf
        $fontOut  = "$fontsDir\$fontFile"
        Invoke-WebRequest -Uri $url -OutFile $fontOut -UseBasicParsing
        Write-Host "    → Police téléchargée : $fontFile" -ForegroundColor DarkGray
    }
    # Réécrire le CSS pour pointer vers les polices locales
    $tablerCssContent = $tablerCssContent -replace "https://cdn\.jsdelivr\.net/npm/@tabler/icons-webfont@[^/]+/fonts/", "../fonts/"
    [System.IO.File]::WriteAllText($tablerCssOut, $tablerCssContent, [System.Text.Encoding]::UTF8)
    Write-Host "[4/6] Polices Tabler téléchargées et CSS mis à jour" -ForegroundColor Green
} else {
    Write-Host "[4/6] Aucune police externe détectée dans Tabler CSS" -ForegroundColor Yellow
}

# ── 5. Patcher ocr_studio.html ────────────────────────────────────────────────
$htmlPath = "$BASE\frontend\templates\ocr_studio.html"
if (-not (Test-Path $htmlPath)) {
    Write-Host "[5/6] ERREUR : $htmlPath introuvable !" -ForegroundColor Red
    exit 1
}

$html = [System.IO.File]::ReadAllText($htmlPath, [System.Text.Encoding]::UTF8)

# Remplacer les CDN par les chemins locaux (servis par FastAPI /static/)
$html = $html -replace 'https://cdn\.jsdelivr\.net/npm/bootstrap@[^"]+/dist/css/bootstrap\.min\.css',
                        '/static/css/bootstrap.min.css'
$html = $html -replace 'https://cdn\.jsdelivr\.net/npm/@tabler/icons-webfont@[^"]+/tabler-icons\.min\.css',
                        '/static/css/tabler-icons.min.css'

[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.Encoding]::UTF8)
Write-Host "[5/6] ocr_studio.html patché (CDN → /static/)" -ForegroundColor Green

# ── 6. Vérifier que FastAPI sert /static/ ─────────────────────────────────────
$mainPath = "$BASE\frontend\main.py"
$mainContent = [System.IO.File]::ReadAllText($mainPath, [System.Text.Encoding]::UTF8)

if ($mainContent -notmatch "StaticFiles") {
    Write-Host "[6/6] ATTENTION : StaticFiles pas trouvé dans frontend/main.py !" -ForegroundColor Yellow
    Write-Host "      Ajoute ces lignes dans frontend/main.py :" -ForegroundColor Yellow
    Write-Host '      from fastapi.staticfiles import StaticFiles' -ForegroundColor White
    Write-Host '      app.mount("/static", StaticFiles(directory="static"), name="static")' -ForegroundColor White
} else {
    Write-Host "[6/6] StaticFiles déjà configuré dans main.py" -ForegroundColor Green
}

Write-Host "`n✅ Terminé ! Redémarre le frontend pour appliquer :" -ForegroundColor Cyan
Write-Host "   cd $BASE\frontend" -ForegroundColor White
Write-Host "   .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`n" -ForegroundColor White
