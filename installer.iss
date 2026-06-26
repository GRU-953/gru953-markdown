[Setup]
AppName=GRU953 Markdown
AppVersion=4.6.0
AppPublisher=GRU953
AppPublisherURL=https://github.com/GRU-953/gru953-markdown
AppSupportURL=https://github.com/GRU-953/gru953-markdown/issues
AppUpdatesURL=https://github.com/GRU-953/gru953-markdown/releases
DefaultDirName={autopf}\GRU953Markdown
DefaultGroupName=GRU953 Markdown
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=GRU953Markdown-Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\GRU953Markdown.exe
VersionInfoVersion=4.6.0
VersionInfoDescription=GRU953 Markdown Setup
VersionInfoCopyright=Copyright (C) 2024-2026 GRU953

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\GRU953Markdown.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GRU953 Markdown"; Filename: "{app}\GRU953Markdown.exe"
Name: "{group}\Uninstall GRU953 Markdown"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GRU953 Markdown"; Filename: "{app}\GRU953Markdown.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GRU953Markdown.exe"; Description: "Launch GRU953 Markdown"; Flags: nowait postinstall skipifsilent
