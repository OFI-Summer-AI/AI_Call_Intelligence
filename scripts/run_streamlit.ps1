# Start Call Intelligence UI on port 9090 (avoids stuck/default 8501).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Port = 9090
$VenvStreamlit = Join-Path $Root "..\venv\Scripts\streamlit.exe"
if (-not (Test-Path $VenvStreamlit)) {
    $VenvStreamlit = Join-Path $Root "venv\Scripts\streamlit.exe"
}
if (-not (Test-Path $VenvStreamlit)) {
    Write-Error "streamlit.exe not found in venv. Activate venv and pip install -r requirements.txt"
}

Write-Host "Freeing port $Port if something is already listening..."
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "  Stopping PID $($_.OwningProcess)"
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1

Set-Location $Root
$env:PYTHONPATH = $Root
Write-Host ""
Write-Host "Open in your browser:  http://127.0.0.1:$Port"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $VenvStreamlit run (Join-Path $Root "app\frontend\streamlit_app.py") `
    --server.port $Port `
    --server.address 127.0.0.1 `
    --browser.serverAddress 127.0.0.1 `
    --browser.serverPort $Port
