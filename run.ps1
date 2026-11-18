# Start the Discord music bot (production-style, no auto-reload).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Ensure only one Benji process — duplicates cause multi-reply spam and audio lag.
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match [regex]::Escape($PSScriptRoot) -and $_.CommandLine -match 'main\.py' } |
    ForEach-Object {
        Write-Host "Stopping existing bot PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Host "Creating .venv..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\pip.exe install -r requirements.txt
}

.\.venv\Scripts\python.exe main.py
