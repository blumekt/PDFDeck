; ============================================================================
; Universal Installer Script for Inno Setup 6
; ============================================================================
;
; This is a portable template for Electron + Python hybrid applications.
; Copy this file to your project's `installers/` folder and customize.
;
; Features:
; - Multi-language support (EN, PL, DE, FR, ES)
; - Custom wizard pages (About, SmartScreen warning, License)
; - Per-user or system-wide installation
; - 64-bit architecture
; - LZMA2 ultra compression
; - Automatic app termination before install/uninstall
; - Registry entries for version tracking
;
; Usage:
; 1. Copy this file to `installers/{app_name}_installer.iss`
; 2. Replace all {{PLACEHOLDER}} values with your app's values
; 3. Update custom messages for your app
; 4. Run: iscc installers/{app_name}_installer.iss
;
; ============================================================================

; ----------------------------------------------------------------------------
; Application Configuration
; TODO: Replace these values with your application's information
; ----------------------------------------------------------------------------
;
; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
; CRITICAL: AppId MUST BE UNIQUE FOR EACH APPLICATION!
; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
;
; If two different apps share the same AppId, Windows will treat them as
; the same application, causing:
;   - Installation overwrites (one app replaces another)
;   - Uninstall conflicts (removing one breaks the other)
;   - Registry corruption
;
; Generate a new GUID for each project at: https://www.guidgenerator.com/
; Format: {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
;
; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#define MyAppName "{{APP_NAME}}"
#define MyAppVersion "{{VERSION}}"
#define MyAppNumericVersion "{{VERSION}}.0"
#define MyAppPublisher "{{PUBLISHER}}"
#define MyAppURL "{{APP_URL}}"
#define MyAppExeName "{{APP_NAME}}.exe"
#define MyAppAssocName "{{APP_NAME}} Project"
#define MyAppAssocExt ".{{APP_EXT}}"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; Application identity
; TODO: Generate unique GUID at https://www.guidgenerator.com/
AppId={{{{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppNumericVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Installation paths - user can change this
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableDirPage=no
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Output configuration
; TODO: Adjust paths for your project structure
OutputDir=..\release
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}

; Visual configuration
; TODO: Add your icon file
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
; Optional: Add wizard images (164x314 and 55x55 pixels)
; WizardImageFile=assets\wizard.bmp
; WizardSmallImageFile=assets\wizard_small.bmp

; Compression - maximum compression for smallest installer
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Privileges - allow per-user or all-users install
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Architecture - 64-bit only
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Uninstaller
UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

; ----------------------------------------------------------------------------
; Languages
; Add or remove languages as needed
; ----------------------------------------------------------------------------

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ----------------------------------------------------------------------------
; Custom Messages
; TODO: Customize all messages for your application
; ----------------------------------------------------------------------------

[CustomMessages]
; Basic messages
english.LaunchAfterInstall=Launch {#MyAppName} after installation
english.CreateDesktopShortcut=Create a desktop shortcut
english.CreateStartMenuShortcut=Create a Start Menu shortcut
english.InstallingBackend=Installing backend components...
polish.LaunchAfterInstall=Uruchom {#MyAppName} po instalacji
polish.CreateDesktopShortcut=Utworz skrot na pulpicie
polish.CreateStartMenuShortcut=Utworz skrot w menu Start
polish.InstallingBackend=Instalowanie komponentow backendu...
german.LaunchAfterInstall={#MyAppName} nach der Installation starten
german.CreateDesktopShortcut=Desktop-Verknupfung erstellen
german.CreateStartMenuShortcut=Startmenu-Verknupfung erstellen
german.InstallingBackend=Backend-Komponenten werden installiert...
french.LaunchAfterInstall=Lancer {#MyAppName} apres l'installation
french.CreateDesktopShortcut=Creer un raccourci sur le bureau
french.CreateStartMenuShortcut=Creer un raccourci dans le menu Demarrer
french.InstallingBackend=Installation des composants backend...
spanish.LaunchAfterInstall=Iniciar {#MyAppName} despues de la instalacion
spanish.CreateDesktopShortcut=Crear acceso directo en el escritorio
spanish.CreateStartMenuShortcut=Crear acceso directo en el menu Inicio
spanish.InstallingBackend=Instalando componentes del backend...

; ----------------------------------------------------------------------------
; About page - Tell users what your app does
; TODO: Write your own "About" text
; ----------------------------------------------------------------------------

english.AboutTitle=About {#MyAppName}
english.AboutSubtitle=A few words from the author
english.AboutText=Welcome to {#MyAppName}!%n%nThis application does amazing things:%n%n- Feature 1%n- Feature 2%n- Feature 3%n%nI hope you enjoy using it!
polish.AboutTitle=O programie {#MyAppName}
polish.AboutSubtitle=Kilka slow od autora
polish.AboutText=Witaj w {#MyAppName}!%n%nTa aplikacja robi niesamowite rzeczy:%n%n- Funkcja 1%n- Funkcja 2%n- Funkcja 3%n%nMam nadzieje, ze Ci sie spodoba!
german.AboutTitle=Uber {#MyAppName}
german.AboutSubtitle=Ein paar Worte vom Autor
german.AboutText=Willkommen bei {#MyAppName}!%n%nDiese Anwendung macht erstaunliche Dinge:%n%n- Funktion 1%n- Funktion 2%n- Funktion 3%n%nIch hoffe, es gefallt dir!
french.AboutTitle=A propos de {#MyAppName}
french.AboutSubtitle=Quelques mots de l'auteur
french.AboutText=Bienvenue dans {#MyAppName}!%n%nCette application fait des choses incroyables:%n%n- Fonctionnalite 1%n- Fonctionnalite 2%n- Fonctionnalite 3%n%nJ'espere que vous l'apprecierez!
spanish.AboutTitle=Acerca de {#MyAppName}
spanish.AboutSubtitle=Unas palabras del autor
spanish.AboutText=Bienvenido a {#MyAppName}!%n%nEsta aplicacion hace cosas increibles:%n%n- Caracteristica 1%n- Caracteristica 2%n- Caracteristica 3%n%nEspero que te guste!

; ----------------------------------------------------------------------------
; SmartScreen page - Warn users about Windows SmartScreen
; This is important for unsigned apps!
; ----------------------------------------------------------------------------

english.SmartScreenTitle=Windows SmartScreen Information
english.SmartScreenSubtitle=Important information about first launch
english.SmartScreenText=When you first run {#MyAppName}, a blue "Windows protected your PC" window may appear.%n%nThis is normal for applications without a code signing certificate.%n%nTo run the program:%n%n1. Click "More info"%n2. Click "Run anyway"%n%nThe application is safe - the warning appears because we don't have a code signing certificate (~300$/year).%n%nAfter the first run, the warning will not appear again.
polish.SmartScreenTitle=Informacja o Windows SmartScreen
polish.SmartScreenSubtitle=Wazna informacja o pierwszym uruchomieniu
polish.SmartScreenText=Przy pierwszym uruchomieniu {#MyAppName} moze pojawic sie niebieskie okno "Windows chronil ten komputer".%n%nTo normalne dla aplikacji bez certyfikatu cyfrowego.%n%nAby uruchomic program:%n%n1. Kliknij "Wiecej informacji"%n2. Kliknij "Uruchom mimo to"%n%nAplikacja jest bezpieczna - ostrzezenie pojawia sie, bo nie mamy certyfikatu cyfrowego (~300$/rok).%n%nPo pierwszym uruchomieniu ostrzezenie juz sie nie pojawi.
german.SmartScreenTitle=Windows SmartScreen Information
german.SmartScreenSubtitle=Wichtige Information zum ersten Start
german.SmartScreenText=Beim ersten Start von {#MyAppName} kann ein blaues Fenster "Windows hat Ihren PC geschutzt" erscheinen.%n%nDas ist normal fur Anwendungen ohne Code-Signing-Zertifikat.%n%nUm das Programm auszufuhren:%n%n1. Klicken Sie auf "Weitere Informationen"%n2. Klicken Sie auf "Trotzdem ausfuhren"%n%nDie Anwendung ist sicher - die Warnung erscheint, weil wir kein Zertifikat haben (~300$/Jahr).%n%nNach dem ersten Start erscheint die Warnung nicht mehr.
french.SmartScreenTitle=Information Windows SmartScreen
french.SmartScreenSubtitle=Information importante sur le premier lancement
french.SmartScreenText=Lors du premier lancement de {#MyAppName}, une fenetre bleue "Windows a protege votre PC" peut apparaitre.%n%nC'est normal pour les applications sans certificat de signature.%n%nPour executer le programme:%n%n1. Cliquez sur "Informations complementaires"%n2. Cliquez sur "Executer quand meme"%n%nL'application est sure - l'avertissement apparait car nous n'avons pas de certificat (~300$/an).%n%nApres la premiere execution, l'avertissement n'apparaitra plus.
spanish.SmartScreenTitle=Informacion de Windows SmartScreen
spanish.SmartScreenSubtitle=Informacion importante sobre el primer inicio
spanish.SmartScreenText=Al iniciar {#MyAppName} por primera vez, puede aparecer una ventana azul "Windows protegio tu PC".%n%nEsto es normal para aplicaciones sin certificado de firma digital.%n%nPara ejecutar el programa:%n%n1. Haz clic en "Mas informacion"%n2. Haz clic en "Ejecutar de todas formas"%n%nLa aplicacion es segura - la advertencia aparece porque no tenemos certificado (~300$/ano).%n%nDespues de la primera ejecucion, la advertencia no volvera a aparecer.

; ----------------------------------------------------------------------------
; License page - Your license terms
; TODO: Write your own license text
; ----------------------------------------------------------------------------

english.LicenseTitle=License and Freedom of Use
english.LicenseSubtitle=Terms of use
english.LicenseText={#MyAppName} is free software.%n%nYou can use it freely for personal and commercial purposes.%n%nNo warranty is provided - use at your own risk.%n%nFor more information, visit: {#MyAppURL}
polish.LicenseTitle=Licencja i wolnosc uzywania
polish.LicenseSubtitle=Warunki uzytkowania
polish.LicenseText={#MyAppName} jest darmowym oprogramowaniem.%n%nMozesz go uzywac swobodnie do celow prywatnych i komercyjnych.%n%nNie udzielamy gwarancji - uzywasz na wlasne ryzyko.%n%nWiecej informacji: {#MyAppURL}
german.LicenseTitle=Lizenz und Nutzungsfreiheit
german.LicenseSubtitle=Nutzungsbedingungen
german.LicenseText={#MyAppName} ist kostenlose Software.%n%nSie konnen es frei fur personliche und kommerzielle Zwecke nutzen.%n%nKeine Garantie wird gegeben - Nutzung auf eigenes Risiko.%n%nMehr Informationen: {#MyAppURL}
french.LicenseTitle=Licence et liberte d'utilisation
french.LicenseSubtitle=Conditions d'utilisation
french.LicenseText={#MyAppName} est un logiciel gratuit.%n%nVous pouvez l'utiliser librement a des fins personnelles et commerciales.%n%nAucune garantie n'est fournie - utilisez a vos propres risques.%n%nPlus d'informations: {#MyAppURL}
spanish.LicenseTitle=Licencia y libertad de uso
spanish.LicenseSubtitle=Terminos de uso
spanish.LicenseText={#MyAppName} es software gratuito.%n%nPuedes usarlo libremente para fines personales y comerciales.%n%nNo se proporciona garantia - usa bajo tu propio riesgo.%n%nMas informacion: {#MyAppURL}

; ----------------------------------------------------------------------------
; Installation Tasks
; ----------------------------------------------------------------------------

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopShortcut}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "{cm:CreateStartMenuShortcut}"; GroupDescription: "{cm:AdditionalIcons}"

; ----------------------------------------------------------------------------
; Files to Install
; TODO: Adjust source paths for your project structure
; ----------------------------------------------------------------------------

[Files]
; Main application (from electron-builder win-unpacked or PyInstaller dist)
; For Electron apps:
Source: "..\frontend\dist-builder\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; For standalone Python apps:
; Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Application icon for shortcuts
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; ----------------------------------------------------------------------------
; Shortcuts
; ----------------------------------------------------------------------------

[Icons]
; Start Menu shortcut (optional, checked by default)
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: startmenuicon

; Desktop shortcut (optional, unchecked by default)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

; ----------------------------------------------------------------------------
; Post-installation actions
; ----------------------------------------------------------------------------

[Run]
; Launch application after installation (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent unchecked

; ----------------------------------------------------------------------------
; Uninstall cleanup
; ----------------------------------------------------------------------------

[UninstallDelete]
; Clean up user data on uninstall (only logs and cache, not user settings)
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"

; ----------------------------------------------------------------------------
; Registry entries
; ----------------------------------------------------------------------------

[Registry]
; Register application in Windows
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ----------------------------------------------------------------------------
; Pascal Script - Custom Wizard Pages
; ----------------------------------------------------------------------------

[Code]
var
  AboutPage: TWizardPage;
  SmartScreenPage: TWizardPage;
  LicensePage: TWizardPage;
  AboutMemo: TNewMemo;
  SmartScreenMemo: TNewMemo;
  LicenseMemo: TNewMemo;

// Create custom wizard pages
procedure InitializeWizard();
begin
  // Page 1: About the application
  AboutPage := CreateCustomPage(wpWelcome,
    CustomMessage('AboutTitle'),
    CustomMessage('AboutSubtitle'));

  AboutMemo := TNewMemo.Create(AboutPage);
  AboutMemo.Parent := AboutPage.Surface;
  AboutMemo.Left := 0;
  AboutMemo.Top := 0;
  AboutMemo.Width := AboutPage.SurfaceWidth;
  AboutMemo.Height := AboutPage.SurfaceHeight;
  AboutMemo.ScrollBars := ssVertical;
  AboutMemo.ReadOnly := True;
  AboutMemo.WordWrap := True;
  AboutMemo.Text := CustomMessage('AboutText');
  AboutMemo.TabStop := False;

  // Page 2: SmartScreen Information
  SmartScreenPage := CreateCustomPage(AboutPage.ID,
    CustomMessage('SmartScreenTitle'),
    CustomMessage('SmartScreenSubtitle'));

  SmartScreenMemo := TNewMemo.Create(SmartScreenPage);
  SmartScreenMemo.Parent := SmartScreenPage.Surface;
  SmartScreenMemo.Left := 0;
  SmartScreenMemo.Top := 0;
  SmartScreenMemo.Width := SmartScreenPage.SurfaceWidth;
  SmartScreenMemo.Height := SmartScreenPage.SurfaceHeight;
  SmartScreenMemo.ScrollBars := ssVertical;
  SmartScreenMemo.ReadOnly := True;
  SmartScreenMemo.WordWrap := True;
  SmartScreenMemo.Text := CustomMessage('SmartScreenText');
  SmartScreenMemo.TabStop := False;

  // Page 3: License and Freedom
  LicensePage := CreateCustomPage(SmartScreenPage.ID,
    CustomMessage('LicenseTitle'),
    CustomMessage('LicenseSubtitle'));

  LicenseMemo := TNewMemo.Create(LicensePage);
  LicenseMemo.Parent := LicensePage.Surface;
  LicenseMemo.Left := 0;
  LicenseMemo.Top := 0;
  LicenseMemo.Width := LicensePage.SurfaceWidth;
  LicenseMemo.Height := LicensePage.SurfaceHeight;
  LicenseMemo.ScrollBars := ssVertical;
  LicenseMemo.ReadOnly := True;
  LicenseMemo.WordWrap := True;
  LicenseMemo.Text := CustomMessage('LicenseText');
  LicenseMemo.TabStop := False;
end;

// Utility function to check if application is running
function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // If tasklist finds the process, it returns 0
    Result := (ResultCode = 0);
  end;
end;

// Close running application before installation
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check if app is running and terminate it
  if Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Wait a moment for process to terminate
    Sleep(500);
  end;
end;

// Close running application before uninstall
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Force close the application if running
  Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
end;
