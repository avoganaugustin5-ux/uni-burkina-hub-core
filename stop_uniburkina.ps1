# UniBurkina Hub - Script d'arret complet
# Usage : .\stop_uniburkina.ps1

Write-Host ""
Write-Host "=================================================" -ForegroundColor Red
Write-Host "   UniBurkina Hub - Arret des services           " -ForegroundColor Red
Write-Host "=================================================" -ForegroundColor Red
Write-Host ""

# 1 - Arreter les processus uvicorn (tous les services Python)
Write-Host "[1/3] Arret des services Python (uvicorn)..." -ForegroundColor Yellow
$uvicorn = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($uvicorn) {
    $uvicorn | Stop-Process -Force
    Write-Host "      OK - $($uvicorn.Count) processus Python arretes." -ForegroundColor Green
} else {
    Write-Host "      Aucun processus Python en cours." -ForegroundColor DarkGray
}

# 2 - Arreter Elasticsearch (java)
Write-Host "[2/3] Arret d'Elasticsearch..." -ForegroundColor Yellow
$elastic = Get-Process -Name "java" -ErrorAction SilentlyContinue
if ($elastic) {
    $elastic | Stop-Process -Force
    Write-Host "      OK - Elasticsearch arrete." -ForegroundColor Green
} else {
    Write-Host "      Elasticsearch n'etait pas en cours." -ForegroundColor DarkGray
}

# 3 - Arreter MinIO
Write-Host "[3/3] Arret de MinIO..." -ForegroundColor Yellow
$minio = Get-Process -Name "minio*" -ErrorAction SilentlyContinue
if ($minio) {
    $minio | Stop-Process -Force
    Write-Host "      OK - MinIO arrete." -ForegroundColor Green
} else {
    Write-Host "      MinIO n'etait pas en cours." -ForegroundColor DarkGray
}

# Fermer toutes les fenetres PowerShell du projet (sauf celle-ci)
Write-Host ""
Write-Host "Fermeture des fenetres PowerShell des services..." -ForegroundColor Yellow
$currentPID = $PID
Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $currentPID } | Stop-Process -Force
Write-Host "      OK - Fenetres fermees." -ForegroundColor Green

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Tous les services sont arretes.                " -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Entree pour fermer cette fenetre." -ForegroundColor DarkGray
Read-Host
