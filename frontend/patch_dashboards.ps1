# ==============================================================================
# patch_dashboards.ps1 - UniBurkina Hub - Correctif v2.1
# Lancer depuis : C:\projets\UniBurkina_Hub\frontend\
#   powershell -ExecutionPolicy Bypass -File .\patch_dashboards.ps1
# ==============================================================================

$base   = "C:\projets\UniBurkina_Hub\frontend"
$tplDir = "$base\templates"

Write-Host ""
Write-Host "=== UniBurkina Hub - Patch Dashboards ===" -ForegroundColor Cyan

# ── ETAPE 1 : Deplacer les templates ──────────────────────────────────────────
Write-Host "[1/3] Deplacement des templates..." -ForegroundColor Yellow

foreach ($f in @("ocr_studio.html","validation_hub.html")) {
    $src = "$base\$f"
    $dst = "$tplDir\$f"
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "      [OK] $f copie vers templates/" -ForegroundColor Green
    } elseif (Test-Path $dst) {
        Write-Host "      [OK] $f deja en place" -ForegroundColor Green
    } else {
        Write-Host "      [WARN] $f introuvable" -ForegroundColor Yellow
    }
}

# ── ETAPE 2 : Lire les snippets HTML depuis fichiers externes ─────────────────
Write-Host "[2/3] Chargement des snippets HTML..." -ForegroundColor Yellow

$btnOCRPath   = "$base\btn_ocr.html"
$btnValidPath = "$base\btn_valid.html"

if (-not (Test-Path $btnOCRPath)) {
    Write-Host "      [ERREUR] btn_ocr.html absent - copiez-le dans frontend/" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $btnValidPath)) {
    Write-Host "      [ERREUR] btn_valid.html absent - copiez-le dans frontend/" -ForegroundColor Red
    exit 1
}

$btnOCR   = [System.IO.File]::ReadAllText($btnOCRPath,   [System.Text.Encoding]::UTF8)
$btnVALID = [System.IO.File]::ReadAllText($btnValidPath, [System.Text.Encoding]::UTF8)

Write-Host "      [OK] Snippets charges" -ForegroundColor Green

# ── ETAPE 3 : Patcher les dashboards ──────────────────────────────────────────
Write-Host "[3/3] Injection des boutons..." -ForegroundColor Yellow

$dashOCR = @(
    "etudiant_dashboard.html",
    "delegue_dashboard.html",
    "enseignant_dashboard.html",
    "sous_admin_dashboard.html",
    "chef_dept_dashboard.html",
    "admin_dashboard.html"
)

$dashVALID = @(
    "sous_admin_dashboard.html",
    "chef_dept_dashboard.html",
    "admin_dashboard.html"
)

$nOCR = 0; $nVALID = 0; $nSkip = 0

foreach ($fname in $dashOCR) {
    $fpath = "$tplDir\$fname"
    if (-not (Test-Path $fpath)) {
        Write-Host "      [SKIP] $fname absent" -ForegroundColor Gray
        $nSkip++
        continue
    }
    $content = [System.IO.File]::ReadAllText($fpath, [System.Text.Encoding]::UTF8)
    if ($content.Contains("OCR_STUDIO_BTN_START")) {
        Write-Host "      [OK]   $fname - OCR deja present" -ForegroundColor Green
    } else {
        $newContent = $content.Replace("</body>", $btnOCR + "`n</body>")
        [System.IO.File]::WriteAllText($fpath, $newContent, [System.Text.Encoding]::UTF8)
        Write-Host "      [PATCH] $fname - OCR Studio injecte" -ForegroundColor Cyan
        $nOCR++
    }
}

foreach ($fname in $dashVALID) {
    $fpath = "$tplDir\$fname"
    if (-not (Test-Path $fpath)) { continue }
    $content = [System.IO.File]::ReadAllText($fpath, [System.Text.Encoding]::UTF8)
    if ($content.Contains("VALIDATION_HUB_BTN_START")) {
        Write-Host "      [OK]   $fname - Validation deja present" -ForegroundColor Green
    } else {
        $newContent = $content.Replace("</body>", $btnVALID + "`n</body>")
        [System.IO.File]::WriteAllText($fpath, $newContent, [System.Text.Encoding]::UTF8)
        Write-Host "      [PATCH] $fname - Validation Hub injecte" -ForegroundColor Cyan
        $nVALID++
    }
}

Write-Host ""
Write-Host "=== Resultat ===" -ForegroundColor Cyan
Write-Host "  Boutons OCR Studio injectes    : $nOCR" -ForegroundColor Green
Write-Host "  Boutons Validation Hub injectes : $nVALID" -ForegroundColor Green
Write-Host "  Fichiers absents ignores        : $nSkip" -ForegroundColor Gray
Write-Host ""
Write-Host "Redemarrez le frontend :" -ForegroundColor White
Write-Host "  .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "Bouton violet [OCR Studio]      visible en bas a droite de chaque dashboard" -ForegroundColor Magenta
Write-Host "Bouton bleu   [Validation Hub]  visible pour sous-admin / chef-dept / admin" -ForegroundColor Blue
