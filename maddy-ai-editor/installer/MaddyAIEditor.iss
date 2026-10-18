#define AppName "Maddy AI Video Editor"
[Setup]
AppId={{7DCB34EC-4924-4DD5-9F88-B4913F941F62}
AppName={#AppName}
AppVersion=1.0
AppVerName=Maddy AI Video Editor 1.0 Development Preview
AppPublisher=Madan
DefaultDirName={localappdata}\Programs\MaddyAIEditor
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir=..\dist
OutputBaseFilename=MaddyAIEditor_Setup_v1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MaddyAIEditor.exe
InfoBeforeFile=preview-notice.txt

[Files]
Source: "..\dist\MaddyAIEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\MaddyAIEditor.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MaddyAIEditor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MaddyAIEditor.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
