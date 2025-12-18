; CV Studio - Inno Setup Installer Script
; Creates a Windows installer for CV Studio
; Includes all dependencies: ONNX Runtime, Python runtime, models, etc.

#define MyAppName "CV Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "hackolite"
#define MyAppURL "https://github.com/hackolite/CV_Studio"
#define MyAppExeName "CV_Studio.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{CV-Studio-B8E7F9A1-5D23-4C8E-9B7F-3A2D8E6F1C4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
; Uncomment the following line to run in non administrative install mode
; (install for current user only.)
;PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=CV_Studio_Setup_v{#MyAppVersion}
; SetupIconFile=node_editor\setting\icon.ico  ; Uncomment if you have an icon file
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Minimum Windows version
MinVersion=6.1sp1
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "dist\CV_Studio\CV_Studio.exe"; DestDir: "{app}"; Flags: ignoreversion
; All other files from the build
Source: "dist\CV_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Message: String;
begin
  Result := True;
  
  // Check for Visual C++ Redistributable
  Message := 'CV Studio requires Microsoft Visual C++ Redistributable.' + #13#10 +
             'If the application fails to start after installation,' + #13#10 +
             'please download and install it from:' + #13#10 + #13#10 +
             'https://aka.ms/vs/17/release/vc_redist.x64.exe' + #13#10 + #13#10 +
             'Continue with installation?';
  
  if MsgBox(Message, mbInformation, MB_YESNO) = IDNO then
  begin
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create a file with system information
    SaveStringToFile(ExpandConstant('{app}\SYSTEM_INFO.txt'), 
      'Installation completed on: ' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', #0, #0) + #13#10 +
      'Installation path: ' + ExpandConstant('{app}') + #13#10 +
      'Windows version: ' + GetWindowsVersionString() + #13#10 + #13#10 +
      'For support, visit: ' + '{#MyAppURL}' + #13#10, False);
  end;
end;

[Messages]
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%nCV Studio is a professional node-based computer vision application that includes:%n%n* Real-time image and video processing%n* ONNX model support for AI/ML%n* 100+ built-in processing nodes%n* GPU acceleration support%n%nIt is recommended that you close all other applications before continuing.
french.WelcomeLabel2=Ceci installera [name/ver] sur votre ordinateur.%n%nCV Studio est une application professionnelle de vision par ordinateur basée sur des nœuds qui inclut:%n%n* Traitement d'images et de vidéos en temps réel%n* Support des modèles ONNX pour l'IA/ML%n* Plus de 100 nœuds de traitement intégrés%n* Support de l'accélération GPU%n%nIl est recommandé de fermer toutes les autres applications avant de continuer.
