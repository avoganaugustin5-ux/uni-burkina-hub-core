# inject_endpoints.ps1
# Injecte les 2 endpoints manquants dans service-ocr/main.py
# Lancer depuis C:\projets\UniBurkina_Hub\service-ocr\
#   powershell -ExecutionPolicy Bypass -File .\inject_endpoints.ps1

$mainPy   = "C:\projets\UniBurkina_Hub\service-ocr\main.py"
$snippetF = "C:\projets\UniBurkina_Hub\service-ocr\endpoints_manquants.py"

Write-Host "=== Injection endpoints OCR manquants ===" -ForegroundColor Cyan

if (-not (Test-Path $mainPy)) {
    Write-Host "[ERREUR] main.py introuvable : $mainPy" -ForegroundColor Red; exit 1
}
if (-not (Test-Path $snippetF)) {
    Write-Host "[ERREUR] endpoints_manquants.py introuvable : $snippetF" -ForegroundColor Red; exit 1
}

$content = [System.IO.File]::ReadAllText($mainPy,   [System.Text.Encoding]::UTF8)
$snippet = [System.IO.File]::ReadAllText($snippetF, [System.Text.Encoding]::UTF8)

if ($content.Contains("/ocr/retranscrire")) {
    Write-Host "[OK] /ocr/retranscrire deja present — rien a faire" -ForegroundColor Green
} else {
    $marker = "# -- 8. SCAN SIMPLE + GED"
    $marker2 = "# ── 8. SCAN SIMPLE + GED"
    $marker3 = "@app.post(`"/ocr/scan-et-ged`""
    $inserted = $false

    foreach ($m in @($marker, $marker2, $marker3)) {
        if ($content.Contains($m)) {
            $newContent = $content.Replace($m, $snippet + "`n`n" + $m)
            [System.IO.File]::WriteAllText($mainPy, $newContent, [System.Text.Encoding]::UTF8)
            Write-Host "[OK] Endpoints injectes avant : $m" -ForegroundColor Green
            $inserted = $true
            break
        }
    }

    if (-not $inserted) {
        # Fallback : ajouter a la fin avant le health check
        $healthMarker = "# -- 12. HEALTH CHECK"
        $healthMarker2 = "# ── 12. HEALTH CHECK"
        $healthMarker3 = "@app.get(`"/health`")"
        foreach ($m in @($healthMarker, $healthMarker2, $healthMarker3)) {
            if ($content.Contains($m)) {
                $newContent = $content.Replace($m, $snippet + "`n`n" + $m)
                [System.IO.File]::WriteAllText($mainPy, $newContent, [System.Text.Encoding]::UTF8)
                Write-Host "[OK] Endpoints injectes avant health check" -ForegroundColor Green
                $inserted = $true
                break
            }
        }
    }

    if (-not $inserted) {
        Write-Host "[WARN] Marqueur non trouve — ajout a la fin du fichier" -ForegroundColor Yellow
        $newContent = $content + "`n`n" + $snippet
        [System.IO.File]::WriteAllText($mainPy, $newContent, [System.Text.Encoding]::UTF8)
        Write-Host "[OK] Endpoints ajoutes en fin de fichier" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Redemarrez service-ocr :" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8003 --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "Verifiez sur : http://localhost:8003/docs" -ForegroundColor White
Write-Host "  -> POST /ocr/retranscrire     doit apparaitre" -ForegroundColor Green
Write-Host "  -> POST /ocr/generer-document doit apparaitre" -ForegroundColor Green
