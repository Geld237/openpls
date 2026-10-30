; Installateur Windows d'OpenPLS (Inno Setup 6). Construit par .github/workflows/release.yml :
;   iscc /DAppVersion=0.4.1 packaging\openpls.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{E587DE54-BE1C-47F4-9EFE-03767BDAAD4A}
AppName=OpenPLS
AppVersion={#AppVersion}
AppPublisher=OpenPLS
AppPublisherURL=https://github.com/Geld237/openpls
DefaultDirName={autopf}\OpenPLS
DefaultGroupName=OpenPLS
; installation pour l'utilisateur courant : aucun droit administrateur requis
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=OpenPLS-{#AppVersion}-Windows-installateur
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\OpenPLS.exe

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\OpenPLS\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\OpenPLS"; Filename: "{app}\OpenPLS.exe"
Name: "{group}\Désinstaller OpenPLS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OpenPLS"; Filename: "{app}\OpenPLS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OpenPLS.exe"; Description: "Lancer OpenPLS"; Flags: nowait postinstall skipifsilent
