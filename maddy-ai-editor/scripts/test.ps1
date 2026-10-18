$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & '.\.venv\Scripts\python.exe' -m pytest -q --junitxml=artifacts/test-results.xml
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & '.\.venv\Scripts\python.exe' -m apps.desktop.main --smoke --settings artifacts/settings.json --screenshot artifacts/desktop.png
    if ($LASTEXITCODE -ne 0) { throw 'Desktop smoke failed' }
} finally { Pop-Location }
