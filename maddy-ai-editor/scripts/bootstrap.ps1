param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & $Python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 x64 required'"
    if ($LASTEXITCODE -ne 0) { throw 'Incorrect Python runtime' }
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'venv failed' }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.lock
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
} finally { Pop-Location }
