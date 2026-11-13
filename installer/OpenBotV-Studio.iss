; OpenBotV Studio — Instalador (Inno Setup 6)
; Compilar con:  ISCC.exe installer\OpenBotV-Studio.iss  (desde la raíz)
; Requiere antes: pyinstaller installer\main.spec --noconfirm

[Setup]
; AppId fijo: identifica la app ante Windows para desinstalar/actualizar.
AppId={{C9D01377-4407-4B19-8A57-F485EFE9E46F}
AppName=OpenBotV Studio
AppVersion=0.6.3
AppVerName=OpenBotV Studio v0.6.3-beta
AppPublisher=Jhon D. Velez & Jeisson I. Sanchez
DefaultDirName={autopf}\OpenBotV-Studio
DisableProgramGroupPage=yes
; Permite elegir al usuario: instalación para todos (requiere admin) o solo para el actual.
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\OpenBotV-Studio.exe
OutputDir=..\dist\installer
OutputBaseFilename=OpenBotV-Studio-Setup
SetupIconFile=..\src\resources\img\laser_b.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\OpenBotV-Studio\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\OpenBotV Studio"; Filename: "{app}\OpenBotV-Studio.exe"
Name: "{autodesktop}\OpenBotV Studio"; Filename: "{app}\OpenBotV-Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OpenBotV-Studio.exe"; Description: "Ejecutar OpenBotV Studio"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpia los logs de la app (~/Documents/OpenBotVStudio/logs) del usuario
; que desinstala.
Type: filesandordirs; Name: "{userdocs}\OpenBotVStudio\logs"
