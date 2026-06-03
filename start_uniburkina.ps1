# UniBurkina Hub - Script de demarrage complet
# AVOGAN Koudjo Augustin Sandaogo - UTS Burkina Faso
# Usage : .\start_uniburkina.ps1

$Host.UI.RawUI.WindowTitle = "UniBurkina Hub - Demarrage"
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "   UniBurkina Hub - Demarrage des services       " -ForegroundColor Cyan
Write-Host "   UTS Burkina Faso - AVOGAN Augustin            " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

function Start-Service-Window {
    param(
        [string]$Titre,
        [string]$Couleur,
        [string]$Commande
    )
    $script = "
`$Host.UI.RawUI.WindowTitle = '$Titre'
Write-Host '[$Titre]' -ForegroundColor $Couleur
Write-Host '------------------------------------------' -ForegroundColor DarkGray
$Commande
Write-Host ''
Write-Host 'Processus termine. Appuyez sur Entree pour fermer.'
Read-Host
"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $script
}

# 1 - Elasticsearch
Write-Host "[1/8] Demarrage Elasticsearch 8.13.4..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "Elasticsearch :9200" `
    -Couleur "Green" `
    -Commande "cd C:\elastic\elasticsearch-8.13.4; bin\elasticsearch.bat"

Write-Host "      Attente 15s pour Elasticsearch..." -ForegroundColor DarkGray
Start-Sleep -Seconds 15

# 2 - MinIO
Write-Host "[2/8] Demarrage MinIO :9000/:9001..." -ForegroundColor Yellow
$minioCmd = '$env:MINIO_ROOT_USER = "uniburkina_admin"; $env:MINIO_ROOT_PASSWORD = "UTS_Minio2025!"; C:\minio\minio.windows-amd64.RELEASE.2025-09-07T16-13-09Z.exe server C:\projets\uniburkina\minio-data --console-address ":9001"'
Start-Service-Window -Titre "MinIO :9000" -Couleur "Cyan" -Commande $minioCmd

Write-Host "      Attente 30s pour MinIO..." -ForegroundColor DarkGray
Start-Sleep -Seconds 30

# 3 - service-auth
Write-Host "[3/8] Demarrage service-auth :8001..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-auth :8001" `
    -Couleur "Magenta" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-auth; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

Start-Sleep -Seconds 3

# 4 - service-ged
Write-Host "[4/8] Demarrage service-ged :8002..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-ged :8002" `
    -Couleur "Magenta" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-ged; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload"

Start-Sleep -Seconds 3

# 5 - service-ocr SANS --reload
Write-Host "[5/8] Demarrage service-ocr :8003 (SANS --reload)..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-ocr :8003 SANS-reload" `
    -Couleur "Red" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-ocr; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8003"

Write-Host "      Attente 60s (PaddleOCR charge ses modeles, soyez patient)..." -ForegroundColor DarkGray
Start-Sleep -Seconds 60

# 6 - service-search
Write-Host "[6/8] Demarrage service-search :8004..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-search :8004" `
    -Couleur "Blue" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-search; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload"

Start-Sleep -Seconds 3

# 7 - service-forum
Write-Host "[7/8] Demarrage service-forum :8005..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-forum :8005" `
    -Couleur "Blue" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-forum; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload"

Start-Sleep -Seconds 3

# 8 - frontend EN DERNIER
Write-Host "[8/8] Demarrage frontend :8000 (EN DERNIER)..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "frontend :8000" `
    -Couleur "Green" `
    -Commande "cd C:\projets\UniBurkina_Hub\frontend; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Tous les services ont ete lances !             " -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Elasticsearch  ->  http://localhost:9200       " -ForegroundColor White
Write-Host "  MinIO Console  ->  http://localhost:9001       " -ForegroundColor White
Write-Host "  service-auth   ->  http://localhost:8001/docs  " -ForegroundColor White
Write-Host "  service-ged    ->  http://localhost:8002/docs  " -ForegroundColor White
Write-Host "  service-ocr    ->  http://localhost:8003/health" -ForegroundColor White
Write-Host "  service-search ->  http://localhost:8004/docs  " -ForegroundColor White
Write-Host "  service-forum  ->  http://localhost:8005/docs  " -ForegroundColor White
Write-Host "  Frontend       ->  http://localhost:8000       " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Entree pour fermer cette fenetre." -ForegroundColor DarkGray
Read-Host
