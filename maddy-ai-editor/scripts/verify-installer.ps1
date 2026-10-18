$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$workspaceRoot = [IO.Path]::GetFullPath('C:\Users\madmin\Documents\Codex')
$installRoot = [IO.Path]::GetFullPath((Join-Path $appRoot 'artifacts\install-test'))
if (!$installRoot.StartsWith($workspaceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Test installation escaped workspace' }
if (Test-Path -LiteralPath $installRoot) { throw 'Test install directory already exists; refusing to overwrite' }
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7DCB34EC-4924-4DD5-9F88-B4913F941F62}_is1'
if (Test-Path -LiteralPath $uninstallKey) { throw 'An existing Maddy installation was found; refusing to replace it' }
$installer = Join-Path $appRoot 'dist\MaddyAIEditor_Setup_v1.0.exe'
$setupProcess = Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',"/DIR=$installRoot", "/LOG=$appRoot\artifacts\install.log" -WindowStyle Hidden -PassThru
if (!$setupProcess.WaitForExit(60000)) { throw 'Test installer timed out' }
$setupProcess.Refresh()
if ($setupProcess.ExitCode -ne 0) { throw "Installer failed: $($setupProcess.ExitCode)" }
$installedExe = Join-Path $installRoot 'MaddyAIEditor.exe'
if (!(Test-Path -LiteralPath $installedExe)) { throw 'Installed EXE missing' }
$registryEntry = Get-ItemProperty -LiteralPath $uninstallKey
if ($registryEntry.InstallLocation.TrimEnd('\') -ne $installRoot) { throw 'Uninstall entry points outside isolated installation' }
$smokeProcess = Start-Process -FilePath $installedExe -ArgumentList '--smoke','--smoke-media',"$appRoot\samples\generated\review-fixture.mp4",'--settings',"$appRoot\artifacts\settings.json",'--screenshot',"$appRoot\artifacts\installed-analysis.png" -WindowStyle Hidden -PassThru
if (!$smokeProcess.WaitForExit(60000)) { throw 'Installed application smoke timed out' }
$smokeProcess.Refresh()
if ($smokeProcess.ExitCode -ne 0) { throw "Installed smoke failed: $($smokeProcess.ExitCode)" }
if (!(Test-Path -LiteralPath "$appRoot\artifacts\installed-analysis.png")) { throw 'Installed smoke screenshot missing' }
# Uninstall only the generated executable inside the checked isolated target.
$uninstaller = [IO.Path]::GetFullPath((Join-Path $installRoot 'unins000.exe'))
if (!(Test-Path -LiteralPath $uninstaller) -or !([IO.Path]::GetDirectoryName($uninstaller) -eq $installRoot)) { throw 'Uninstaller validation failed' }
$removeProcess = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -WindowStyle Hidden -PassThru
if (!$removeProcess.WaitForExit(60000)) { throw 'Test uninstaller timed out' }
$removeProcess.Refresh()
if ($removeProcess.ExitCode -ne 0) { throw "Uninstaller failed: $($removeProcess.ExitCode)" }
$result = [ordered]@{
    host = 'Windows 11 build 26200, existing development machine'
    clean_vm = $false
    install_exit = $setupProcess.ExitCode
    application_exit = $smokeProcess.ExitCode
    uninstall_exit = $removeProcess.ExitCode
    executable_removed = !(Test-Path -LiteralPath $installedExe)
    uninstall_entry_removed = !(Test-Path -LiteralPath $uninstallKey)
    installer_sha256 = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
}
$result | ConvertTo-Json | Set-Content -LiteralPath "$appRoot\artifacts\installer-verification.json" -Encoding utf8
$result | ConvertTo-Json
if (!$result.executable_removed -or !$result.uninstall_entry_removed) { throw 'Uninstall verification failed' }
