# Dev loop: restart main.py whenever a .py file changes (Shiori-style reload).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Kill stray bot processes first (multiple instances = spam replies + lag).
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

$python = Resolve-Path .\.venv\Scripts\python.exe
Write-Host "Watching *.py — save a file to restart the bot. Ctrl+C to stop."
Write-Host "Important: run only ONE dev.ps1 / run.ps1 at a time."
& $python -m watchfiles --filter python "$python main.py" .
