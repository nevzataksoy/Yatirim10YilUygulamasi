; Rosa Investment Engine v1.2.0
; Single-file PyInstaller EXE + Windows Service installation

#define MyAppName "Rosa Investment Engine"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Rosa Yazılım ve Bilgi Teknolojileri San. ve Tic. Ltd. Şti."
#define MyAppURL "https://rosayazilim.tr"
#define MyAppExeName "InvestmentEngine.exe"
#define MyServiceName "RosaInvestmentEngine"

[Setup]
AppId={{8B2C6391-6651-4D6C-A5D6-B744A1C28FC5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Rosa\InvestmentEngine
DefaultGroupName=Rosa\InvestmentEngine
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Kurulum Dosyası
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=InvestmentEngineSetup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
; settings ve rosalock {app} altında runtime'da oluşturulur.
; Program Files + admin/UAC + dosya DACL'i birlikte güvenlik sınırını oluşturur.
Name: "{app}\logs"
Name: "{app}\runtime"
Name: "{app}\migrations"
Name: "{app}\docs"
; Firebase service-account JSON installer'a dahil edilmez. Yalnız sunucuya özel
; credential dizini oluşturulur ve uninstall/upgrade sırasında korunur.
Name: "{commonappdata}\Rosa\InvestmentEngine\secrets"; Permissions: admins-full system-full; Flags: uninsneveruninstall

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "InvestmentEngineCLI.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "InvestmentEngineCLI.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "migrations\*.sql"; DestDir: "{app}\migrations"; Flags: ignoreversion
Source: "docs\*.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Rosa\Investment Engine Ayarları"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Investment Engine Ayarları"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; İlk kurulumda settings yoksa ayar ekranını aç. EXE UAC manifesti nedeniyle yönetici olarak çalışır.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--configure"; WorkingDir: "{app}"; StatusMsg: "Investment Engine ilk ayarları açılıyor..."; Flags: waituntilterminated; Check: NeedInitialConfiguration

; Tek EXE Windows Service olarak kaydedilir. Kurulum idempotenttir: eski service kaydı silinip yeniden oluşturulur.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-service"; WorkingDir: "{app}"; StatusMsg: "Windows Service kuruluyor..."; Flags: runhidden waituntilterminated

; Ayarlar başarıyla oluşturulduysa servisi başlat.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--start-service"; WorkingDir: "{app}"; StatusMsg: "Investment Engine servisi başlatılıyor..."; Flags: runhidden waituntilterminated; Check: EngineConfigured

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--stop-service"; Flags: runhidden waituntilterminated; RunOnceId: "StopInvestmentEngine"
Filename: "{app}\{#MyAppExeName}"; Parameters: "--uninstall-service"; Flags: runhidden waituntilterminated; RunOnceId: "DeleteInvestmentEngineService"

[Code]
function NeedInitialConfiguration(): Boolean;
begin
  Result := not (FileExists(ExpandConstant('{app}\settings')) and FileExists(ExpandConstant('{app}\rosalock')));
end;

function EngineConfigured(): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\settings')) and FileExists(ExpandConstant('{app}\rosalock'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  { Upgrade sırasında çalışan servisi durdur; ilk kurulumda hata kodu önemsenmez. }
  Exec(ExpandConstant('{sys}\net.exe'), 'stop {#MyServiceName} /y', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Generated settings/rosalock setup paketine dahil değildir ve upgrade sırasında korunur. }
  end;
end;
