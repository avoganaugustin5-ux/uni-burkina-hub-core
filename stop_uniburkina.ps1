# UniBurkina Hub - Script d'arret complet (v2 - ciblage precis par port)
# Usage : .\stop_uniburkina.ps1
#
# Changement par rapport a la v1 :
#   - L'ancienne version tuait TOUS les processus nommes "python" et TOUTES
#     les fenetres "powershell" de la machine (Get-Process -Name "python" / "powershell"
#     sans filtre) -> risque reel de fermer d'autres projets Python, Jupyter,
#     VS Code, ou fenetres PowerShell sans rapport avec UniBurkina Hub.
#   - Cette version arrete UNIQUEMENT les processus qui ecoutent reellement
#     sur les ports du projet (8000-8005, 9000, 9001, 9200), et ferme en plus
#     la fenetre PowerShell "wrapper" qui les a lances (si elle existe),
#     sans toucher a quoi que ce soit d'autre sur la machine.

Write-Host ""
Write-Host "=================================================" -ForegroundColor Red
Write-Host "   UniBurkina Hub - Arret des services           " -ForegroundColor Red
Write-Host "=================================================" -ForegroundColor Red
Write-Host ""

# Ports utilises par le projet UniBurkina Hub
$ports = [ordered]@{
    8000 = "frontend"
    8001 = "service-auth"
    8002 = "service-ged"
    8003 = "service-ocr"
    8004 = "service-search"
    8005 = "service-forum"
    9000 = "MinIO (API)"
    9001 = "MinIO (Console)"
    9200 = "Elasticsearch"
}

$arretes = 0

foreach ($port in $ports.Keys) {
    $label = $ports[$port]
    try {
        $connexions = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    } catch {
        $connexions = $null
    }

    if (-not $connexions) {
        Write-Host "[$label :$port] Rien a l'ecoute sur ce port - deja arrete." -ForegroundColor DarkGray
        continue
    }

    foreach ($conn in $connexions) {
        $procId = $conn.OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) { continue }

        Write-Host "[$label :$port] Arret de $($proc.ProcessName) (PID $procId)..." -ForegroundColor Yellow

        # Retrouver la fenetre PowerShell "wrapper" qui a lance ce processus,
        # pour la fermer aussi (sinon la fenetre reste ouverte, vide).
        $parentId = $null
        try {
            $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).ParentProcessId
        } catch {}

        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue

        if ($parentId) {
            $parentProc = Get-Process -Id $parentId -ErrorAction SilentlyContinue
            if ($parentProc -and $parentProc.ProcessName -match "powershell") {
                Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
                Write-Host "        (fenetre PowerShell associee egalement fermee)" -ForegroundColor DarkGray
            }
        }

        $arretes++
    }
}

Write-Host ""
if ($arretes -gt 0) {
    Write-Host "OK - $arretes processus UniBurkina Hub arretes." -ForegroundColor Green
} else {
    Write-Host "Aucun service UniBurkina Hub n'etait en cours d'execution." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Arret termine (aucun autre processus de la machine touche).  " -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Entree pour fermer cette fenetre." -ForegroundColor DarkGray
Read-Host
