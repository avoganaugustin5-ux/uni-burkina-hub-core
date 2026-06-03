# ===========================================================================
# UniBurkina Hub — Installation des packages etendus pour service-ocr
# CORRECTION : guillemets doubles imbriques corriges avec apostrophes simples
# Executer dans PowerShell depuis le dossier service-ocr :
#   cd C:\projets\UniBurkina_Hub\service-ocr
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\install_packages_fixed.ps1
# ===========================================================================

Write-Host '=== UniBurkina Hub - Installation packages service-ocr ===' -ForegroundColor Cyan

$python = '.\venv\Scripts\python.exe'
$pip    = '.\venv\Scripts\pip.exe'

# Verifier que le venv existe
if (-not (Test-Path $python)) {
    Write-Host '[ERREUR] venv introuvable. Creer le venv d''abord :' -ForegroundColor Red
    Write-Host '  python -m venv venv' -ForegroundColor Yellow
    Write-Host '  .\venv\Scripts\pip.exe install --upgrade pip' -ForegroundColor Yellow
    exit 1
}

# 1. python-docx, openpyxl, python-pptx (generation multi-format)
Write-Host ''
Write-Host '[1/7] Installation python-docx, openpyxl, python-pptx...' -ForegroundColor Yellow
& $pip install 'python-docx==1.1.2' 'openpyxl==3.1.5' 'python-pptx==0.6.23'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur packages documents - continuer' -ForegroundColor Yellow }

# 2. aiosmtplib (email async pour notifications)
Write-Host ''
Write-Host '[2/7] Installation aiosmtplib + email-validator...' -ForegroundColor Yellow
& $pip install 'aiosmtplib==3.0.1' 'email-validator==2.2.0'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur aiosmtplib - continuer' -ForegroundColor Yellow }

# 3. Pillow (traitement images)
Write-Host ''
Write-Host '[3/7] Installation Pillow...' -ForegroundColor Yellow
& $pip install 'Pillow==10.4.0'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur Pillow - continuer' -ForegroundColor Yellow }

# 4. numpy (amelioration images OCR)
Write-Host ''
Write-Host '[4/7] Installation numpy...' -ForegroundColor Yellow
& $pip install 'numpy==1.26.4'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur numpy - continuer' -ForegroundColor Yellow }

# 5. ReportLab (generation PDF)
Write-Host ''
Write-Host '[5/7] Installation reportlab...' -ForegroundColor Yellow
& $pip install 'reportlab==4.2.2'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur reportlab - continuer' -ForegroundColor Yellow }

# 6. httpx + python-multipart + python-dotenv
Write-Host ''
Write-Host '[6/7] Installation httpx, python-multipart, python-dotenv...' -ForegroundColor Yellow
& $pip install 'httpx==0.27.0' 'python-multipart==0.0.9' 'python-dotenv==1.0.1'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur utilitaires - continuer' -ForegroundColor Yellow }

# 7. pytesseract + SQLAlchemy + psycopg2
Write-Host ''
Write-Host '[7/7] Installation pytesseract, sqlalchemy, psycopg2-binary...' -ForegroundColor Yellow
& $pip install 'pytesseract==0.3.13' 'SQLAlchemy==2.0.30' 'psycopg2-binary==2.9.9'
if ($LASTEXITCODE -ne 0) { Write-Host '[WARN] Erreur DB packages - continuer' -ForegroundColor Yellow }

# === Verification ===
Write-Host ''
Write-Host '=== Verification des installations ===' -ForegroundColor Cyan

$checks = @(
    @{ module = 'docx';        label = 'python-docx' },
    @{ module = 'openpyxl';    label = 'openpyxl' },
    @{ module = 'pptx';        label = 'python-pptx' },
    @{ module = 'aiosmtplib';  label = 'aiosmtplib' },
    @{ module = 'PIL';         label = 'Pillow' },
    @{ module = 'numpy';       label = 'numpy' },
    @{ module = 'reportlab';   label = 'reportlab' },
    @{ module = 'pytesseract'; label = 'pytesseract' }
)

$ok = 0
$fail = 0
foreach ($c in $checks) {
    $result = & $python -c "import $($c.module); print('OK')" 2>&1
    if ($result -eq 'OK') {
        Write-Host "  [OK] $($c.label)" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "  [KO] $($c.label) - $result" -ForegroundColor Red
        $fail++
    }
}

Write-Host ''
Write-Host "=== Resultat : $ok OK / $fail echec(s) ===" -ForegroundColor $(if ($fail -eq 0) { 'Green' } else { 'Yellow' })

# === Creer .env UTF-8 si absent ===
if (-not (Test-Path '.env')) {
    Write-Host ''
    Write-Host 'Creation du fichier .env en UTF-8...' -ForegroundColor Cyan
    $envContent = @'
DATABASE_URL=postgresql://uniburkina_admin:UTS_Burkina2025!@localhost:5432/uniburkina_db
API_GED=http://localhost:8002
API_AUTH=http://localhost:8001
OCR_UPLOAD_DIR=uploads/ocr
OCR_OUTPUT_DIR=outputs/ocr
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=avoganaugustin5@gmail.com
SMTP_PASSWORD=REMPLACER_PAR_MOT_DE_PASSE_APPLICATION
SMTP_FROM=avoganaugustin5@gmail.com
SMTP_FROM_NAME=UniBurkina Hub
SECRET_KEY=uniburkina_secret_key_2025
ALGORITHM=HS256
MAX_FILE_SIZE_MB=50
'@
    [System.IO.File]::WriteAllText('.env', $envContent, [System.Text.Encoding]::UTF8)
    Write-Host '  [OK] .env cree en UTF-8' -ForegroundColor Green
} else {
    Write-Host '[INFO] .env existant conserve' -ForegroundColor Gray
}

Write-Host ''
Write-Host '=== Installation terminee ! ===' -ForegroundColor Green
Write-Host 'Lancer le service-ocr avec :' -ForegroundColor White
Write-Host '  .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8003 --reload' -ForegroundColor Gray
