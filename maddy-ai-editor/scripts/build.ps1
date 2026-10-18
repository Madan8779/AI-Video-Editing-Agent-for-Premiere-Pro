param([string]$InnoCompiler = '')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & '.\.venv\Scripts\python.exe' -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --onedir --windowed --name MaddyAIEditor --paths . --collect-submodules uvicorn --collect-data faster_whisper --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.QtPdf --exclude-module PySide6.QtPdfWidgets apps/desktop/main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    New-Item -ItemType Directory -Path dist/MaddyAIEditor/integrations,dist/MaddyAIEditor/docs -Force | Out-Null
    Copy-Item -Path 'integrations\*' -Destination dist/MaddyAIEditor/integrations -Recurse -Force
    Copy-Item -Path 'docs\*' -Destination dist/MaddyAIEditor/docs -Recurse -Force
    Copy-Item -LiteralPath requirements.lock -Destination dist/MaddyAIEditor/requirements.lock -Force
    if (!$InnoCompiler) {
        $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        if (Test-Path -LiteralPath $candidate) { $InnoCompiler = $candidate }
    }
    if ($InnoCompiler) {
        & $InnoCompiler installer/MaddyAIEditor.iss
        if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed' }
    } else { Write-Warning 'Inno Setup not found: executable built; installer remains unbuilt.' }
    Get-ChildItem -LiteralPath dist -Filter '*.exe' -File | Get-FileHash -Algorithm SHA256 | Format-List
} finally { Pop-Location }
