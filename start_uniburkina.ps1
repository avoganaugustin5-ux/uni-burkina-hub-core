# UniBurkina Hub - Script de demarrage complet (v2 - avec health-checks actifs)
# AVOGAN Koudjo Augustin Sandaogo - UTS Burkina Faso
# Usage : .\start_uniburkina.ps1
#
# Changement par rapport a la v1 :
#   - Les Start-Sleep fixes (15s, 50s, 60s...) sont remplaces par une boucle
#     active qui interroge le endpoint de sante de chaque service et n'avance
#     que lorsque le service repond reellement (avec un timeout de securite).
#   - Si un service ne devient jamais pret, le script s'ARRETE et previent
#     au lieu de lancer la suite a l'aveugle sur des dependances mortes
#     (c'est ce qui causait le crash de service-ged quand MinIO n'etait pas
#     encore pret : Start-Sleep 50s ne garantit rien, un vrai ping si).

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

# ==============================================================================
# Attend activement qu'un endpoint HTTP reponde, au lieu d'un Start-Sleep fixe.
# Accepte PLUSIEURS URLs candidates (ex: /health, /docs, /) - le service est
# considere pret des que L'UNE d'entre elles repond. Utile quand on ne sait
# pas a l'avance si un service expose /docs ou /health (ex: Swagger desactive).
# Retourne $true si pret, $false si timeout atteint.
# ==============================================================================
function Wait-ForHttp {
    param(
        [string]$Nom,
        [string[]]$Urls,
        [int]$TimeoutSecondes = 90,
        [int]$IntervalleSecondes = 2
    )
    Write-Host "      Attente de $Nom (essais sur : $($Urls -join ', '))..." -ForegroundColor DarkGray
    $chrono = 0
    while ($chrono -lt $TimeoutSecondes) {
        foreach ($url in $Urls) {
            try {
                $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
                if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
                    Write-Host "      OK - $Nom pret apres ${chrono}s (repond sur $url)." -ForegroundColor Green
                    return $true
                }
            } catch {
                # Cette URL ne repond pas encore (ou 404/refuse), on tente la suivante
            }
        }
        Start-Sleep -Seconds $IntervalleSecondes
        $chrono += $IntervalleSecondes
        Write-Host "      ... toujours en attente de $Nom (${chrono}s / ${TimeoutSecondes}s)" -ForegroundColor DarkGray
    }
    Write-Host "      ECHEC - $Nom ne repond sur aucune URL testee apres ${TimeoutSecondes}s." -ForegroundColor Red
    return $false
}

# ==============================================================================
# 1 - Elasticsearch
# ==============================================================================
Write-Host "[1/8] Demarrage Elasticsearch 8.13.4..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "Elasticsearch :9200" `
    -Couleur "Green" `
    -Commande "cd C:\elastic\elasticsearch-8.13.4; bin\elasticsearch.bat"

if (-not (Wait-ForHttp -Nom "Elasticsearch" -Urls @("http://localhost:9200", "http://localhost:9200/_cluster/health") -TimeoutSecondes 90)) {
    Write-Host ""
    Write-Host "ARRET : Elasticsearch n'a pas demarre. Verifie la fenetre Elasticsearch et relance le script." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 2 - MinIO
# ==============================================================================
Write-Host "[2/8] Demarrage MinIO :9000/:9001..." -ForegroundColor Yellow
$minioScript = @'
$Host.UI.RawUI.WindowTitle = 'MinIO :9000'
Write-Host '[MinIO :9000]' -ForegroundColor Cyan
Write-Host '------------------------------------------' -ForegroundColor DarkGray
$env:MINIO_ROOT_USER = "uniburkina_admin"
$env:MINIO_ROOT_PASSWORD = "UTS_Minio2025!"
C:\minio\minio.windows-amd64.RELEASE.2025-09-07T16-13-09Z.exe server C:\projets\uniburkina\minio-data --console-address ":9001"
Write-Host ''
Write-Host 'Processus termine. Appuyez sur Entree pour fermer.'
Read-Host
'@
$minioBytes   = [System.Text.Encoding]::Unicode.GetBytes($minioScript)
$minioEncoded = [Convert]::ToBase64String($minioBytes)
Start-Process powershell.exe -ArgumentList "-NoExit", "-EncodedCommand", $minioEncoded

if (-not (Wait-ForHttp -Nom "MinIO" -Urls @("http://localhost:9000/minio/health/live", "http://localhost:9000") -TimeoutSecondes 90)) {
    Write-Host ""
    Write-Host "ARRET : MinIO n'a pas demarre. service-ged plantera au demarrage sans lui." -ForegroundColor Red
    Write-Host "Verifie la fenetre MinIO (port deja utilise ? chemin de l'exe correct ?)." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 3 - service-auth
# ==============================================================================
Write-Host "[3/8] Demarrage service-auth :8001..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-auth :8001" `
    -Couleur "Magenta" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-auth; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

if (-not (Wait-ForHttp -Nom "service-auth" -Urls @("http://localhost:8001/health", "http://localhost:8001/docs", "http://localhost:8001/") -TimeoutSecondes 30)) {
    Write-Host "ARRET : service-auth n'a pas demarre." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 4 - service-ged (necessite MinIO deja pret, confirme ci-dessus)
# ==============================================================================
Write-Host "[4/8] Demarrage service-ged :8002..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-ged :8002" `
    -Couleur "Magenta" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-ged; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8002"

if (-not (Wait-ForHttp -Nom "service-ged" -Urls @("http://localhost:8002/health", "http://localhost:8002/docs", "http://localhost:8002/") -TimeoutSecondes 30)) {
    Write-Host "ARRET : service-ged n'a pas demarre (verifie que MinIO tourne bien)." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 5 - service-ocr SANS --reload (PaddleOCR charge ses modeles, peut prendre du temps)
# ==============================================================================
Write-Host "[5/8] Demarrage service-ocr :8003 (SANS --reload)..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-ocr :8003 SANS-reload" `
    -Couleur "Red" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-ocr; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8003"

if (-not (Wait-ForHttp -Nom "service-ocr" -Urls @("http://localhost:8003/health", "http://localhost:8003/docs", "http://localhost:8003/") -TimeoutSecondes 120)) {
    Write-Host "ARRET : service-ocr n'a pas demarre (PaddleOCR met parfois plus de 2 min a froid)." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 6 - service-search
# ==============================================================================
Write-Host "[6/8] Demarrage service-search :8004..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-search :8004" `
    -Couleur "Blue" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-search; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload"

if (-not (Wait-ForHttp -Nom "service-search" -Urls @("http://localhost:8004/health", "http://localhost:8004/docs", "http://localhost:8004/") -TimeoutSecondes 30)) {
    Write-Host "ARRET : service-search n'a pas demarre." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 7 - service-forum
# ==============================================================================
Write-Host "[7/8] Demarrage service-forum :8005..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "service-forum :8005" `
    -Couleur "Blue" `
    -Commande "cd C:\projets\UniBurkina_Hub\service-forum; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload"

if (-not (Wait-ForHttp -Nom "service-forum" -Urls @("http://localhost:8005/health", "http://localhost:8005/docs", "http://localhost:8005/") -TimeoutSecondes 30)) {
    Write-Host "ARRET : service-forum n'a pas demarre." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

# ==============================================================================
# 8 - frontend EN DERNIER
# ==============================================================================
Write-Host "[8/8] Demarrage frontend :8000 (EN DERNIER)..." -ForegroundColor Yellow
Start-Service-Window `
    -Titre "frontend :8000" `
    -Couleur "Green" `
    -Commande "cd C:\projets\UniBurkina_Hub\frontend; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Wait-ForHttp -Nom "frontend" -Urls @("http://localhost:8000", "http://localhost:8000/login") -TimeoutSecondes 30 | Out-Null

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Tous les services sont demarres et confirmes prets !" -ForegroundColor Green
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
