# MediaHub - einheitlicher Nullinstallationstest. Windows PowerShell 5.1.
# v1.0.25: Gemeinsamer Nulltest mit nativer Node-/HTTPS-Tool-Calling-Probe; Release-Stand v0.9.1 / Compute v0.2.1 / Interaktions-KI v0.1.13.
# HTTPS-/CPU-/CUDA-Tests aus erfolgreich getesteter v1.0.19 unveraendert.
# Nur Testordner werden neu angelegt. Kein Git, kein Release, keine .bak.
param(
    [string]$VideoPath = '',
    [string]$TestRoot = '',
    [ValidateSet('all','cpu','gpu')][string]$Mode = 'all',
    [switch]$DiagnosePause,
    [switch]$DiagnoseAlle
)
cls
$ProgrammVersion = '1.0.25-native-toolcalling-bom-diagalle-20261124'
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($DiagnosePause) {
    $Mode = 'cpu'
    Write-Host 'DIAGNOSE: Nur Interaktions-KI CPU; eine Werkzeugrunde; Bereinigung erst nach JA.' -ForegroundColor Yellow
}
$base = 'D:\eigenes program'
$pluginRepo = Join-Path $base 'MediaHub-Plugins'
$nodeRepo = Join-Path $base 'MediaHub-AI-Node'
$sourceDir = Join-Path $pluginRepo 'release'
$ExpectedNodeVersion = '0.9.1'
$ExpectedComputeVersion = '0.2.1'
$ExpectedInteractionVersion = '0.1.13'
if ([string]::IsNullOrWhiteSpace($TestRoot)) {
    $suggested = Join-Path $base 'cheti sicherungs datein\plugin_test'
    $answer = Read-Host "Test-Nullinstallationsordner (Enter = $suggested)"
    $TestRoot = if ([string]::IsNullOrWhiteSpace($answer)) { $suggested } else { $answer.Trim('"') }
}
$testRoot = [IO.Path]::GetFullPath($TestRoot)
$internal = Join-Path $testRoot '_Testskripte_Intern'
$pkgDir = Join-Path $testRoot 'Quellen\MediaHub-Plugins\release'
# Schutz vor versehentlichem Schreiben in die Repositories oder deren Release-Ordner.
foreach ($protected in @($pluginRepo,$nodeRepo,$sourceDir)) {
    $p = [IO.Path]::GetFullPath($protected).TrimEnd('\')
    if ($testRoot.TrimEnd('\').Equals($p,[StringComparison]::OrdinalIgnoreCase) -or
        $testRoot.StartsWith($p+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw "Testordner darf nicht innerhalb eines Projekt-Repositories liegen: $testRoot"
    }
}
$jobs = @(
    @{ id='python_runtime'; pattern='^MediaHub_PythonRuntime_v(.+)\.mhaiplugin$'; label='Python Runtime' },
    @{ id='gliner'; pattern='^MediaHub_GLiNER_v(.+)\.mhaiplugin$'; label='GLiNER' },
    @{ id='smolvlm2'; pattern='^MediaHub_SmolVLM2Vision_v(.+)\.mhaiplugin$'; label='SmolVLM2' },
    @{ id='speech_to_text'; pattern='^MediaHub_Speech-to-Text_v(.+)\.mhaiplugin$'; label='Speech-to-Text' },
    @{ id='interaktions_ki'; pattern='^MediaHub_Interaktions-KI_v(?!.*-dev)(.+)\.mhaiplugin$'; label='Interaktions-KI' }
)
# Nicht-destruktive Pruefung der geplanten Datei-/Ordnerpfade.
function Test-PathDepth([string]$Path,[string]$Kind) {
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetPathRoot($full)
    $relative = $full.Substring($root.Length).TrimEnd('\')
    $parts = if ($relative) { @($relative -split '\\') } else { @() }
    $depth = if ($Kind -eq 'Datei') { [Math]::Max(0,$parts.Count-1) } else { $parts.Count }
    $length = $full.Length
    $status = if ($length -ge 260) { 'KRITISCH' } elseif ($length -ge 220 -or $depth -gt 12) { 'WARNUNG' } else { 'OK' }
    return [pscustomobject]@{Art=$Kind;Tiefe=$depth;Zeichen=$length;Status=$status;Pfad=$full}
}
function Show-PathDepthReport([object[]]$Items) {
    Write-Host "`n===== DATEI- UND ORDNERTIEFE =====" -ForegroundColor Cyan
    $report = @($Items | Sort-Object Pfad -Unique)
    foreach ($entry in $report) {
        $color = if ($entry.Status -eq 'KRITISCH') { 'Red' } elseif ($entry.Status -eq 'WARNUNG') { 'Yellow' } else { 'Gray' }
        Write-Host ("[{0}] {1}: {2} Ebenen, {3} Zeichen - {4}" -f $entry.Status,$entry.Art,$entry.Tiefe,$entry.Zeichen,$entry.Pfad) -ForegroundColor $color
    }
    $critical = @($report | Where-Object { $_.Status -eq 'KRITISCH' }).Count
    $warning = @($report | Where-Object { $_.Status -eq 'WARNUNG' }).Count
    Write-Host "Pfadpruefung: $($report.Count) Pfade, $warning Warnungen, $critical kritisch. Keine Dateien veraendert."
    if ($critical -gt 0) {
        Write-Host 'Pfad ab 260 Zeichen: Bei Windows ohne Long-Path-Unterstuetzung kann die Installation scheitern.' -ForegroundColor Yellow
        if (-not (Confirm 'Trotz kritischer Pfadlaenge fortfahren?')) { throw 'Abbruch wegen kritischer Pfadlaenge.' }
    }
}

function Confirm([string]$Message) {
    # Tippfehler duerfen keine Testvariante stillschweigend ueberspringen.
    while ($true) {
        $answer = (Read-Host "$Message (ja/nein)").Trim()
        if ($answer -match '^(?i:ja)$') { return $true }
        if ($answer -match '^(?i:nein)$') { return $false }
        Write-Host 'Ungueltige Eingabe. Bitte genau ja oder nein eingeben.' -ForegroundColor Yellow
    }
}
function Find-Package([string]$Dir,[string]$Pattern) {
    if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { return @() }
    return @(Get-ChildItem -LiteralPath $Dir -File -Filter '*.mhaiplugin' | Where-Object { $_.Name -match $Pattern } | Sort-Object Name)
}
function Select-One([object[]]$Candidates,[string]$Label) {
    if ($Candidates.Count -eq 0) { return $null }
    if ($Candidates.Count -eq 1) { return $Candidates[0] }
    Write-Host "Mehrere $Label gefunden:" -ForegroundColor Yellow
    for ($i=0;$i -lt $Candidates.Count;$i++) { Write-Host ("  {0}. {1}" -f ($i+1),$Candidates[$i].FullName) }
    $choice=Read-Host 'Nummer (0 = Abbruch)'
    $num=0
    if (-not [int]::TryParse($choice,[ref]$num) -or $num -lt 1 -or $num -gt $Candidates.Count) { throw 'Auswahl abgebrochen.' }
    return $Candidates[$num-1]
}
function Get-Python {
    foreach ($name in @('py','python')) {
        $cmd=Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw 'Python nicht gefunden.'
}
function Run-Python([string]$File,[string[]]$Arguments) {
    $python=Get-Python
    if ([IO.Path]::GetFileName($python).ToLowerInvariant() -eq 'py.exe') { & $python -3 $File @Arguments }
    else { & $python $File @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "Build fehlgeschlagen: $File (ExitCode $LASTEXITCODE)" }
}
function Copy-Safely([string]$From,[string]$To) {
    if (Test-Path -LiteralPath $To -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $From -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $To -Algorithm SHA256).Hash) { return }
        if (-not (Confirm "Vorhandene Quelldatei ersetzen? $To")) { throw 'Quellenaustausch abgebrochen.' }
    }
    Copy-Item -LiteralPath $From -Destination $To -Force -ErrorAction Stop
}
function Build-MissingPlugin([hashtable]$Job) {
    $builder = Join-Path $pluginRepo 'build_plugins.py'
    if (-not (Test-Path -LiteralPath $builder -PathType Leaf)) { throw "Plugin-Buildskript fehlt: $builder" }
    if (-not (Confirm "Paket $($Job.label) fehlt. Jetzt mit dem ORIGINAL-Buildskript bauen?")) { return $false }
    Write-Host "Baue $($Job.id) im Original-Plugin-Repository ..." -ForegroundColor Cyan
    Push-Location $pluginRepo
    try { Run-Python $builder @($Job.id) } finally { Pop-Location }
    if (@(Find-Package $sourceDir $Job.pattern).Count -eq 0) { throw "Build meldete Erfolg, aber das Paket fehlt weiterhin: $($Job.label)" }
    return $true
}
function Build-MissingExe {
    $spec = Join-Path $nodeRepo 'windows_compute_node\MediaHubComputeNode.spec'
    if (-not (Test-Path -LiteralPath $spec -PathType Leaf)) { throw "Original-PyInstaller-Spezifikation fehlt: $spec" }
    if (-not (Confirm 'Compute-Node-EXE fehlt. Jetzt aus dem ORIGINAL-Node-Repository bauen?')) { return $false }
    $dist = Join-Path $nodeRepo 'dist'
    $work = Join-Path $testRoot '_BuildWork\PyInstaller'
    New-Item -ItemType Directory -Path $dist,$work -Force | Out-Null
    $python = Get-Python
    Write-Host 'Baue Compute-Node-EXE mit der Original-Spezifikation ...' -ForegroundColor Cyan
    Push-Location $nodeRepo
    try {
        if ([IO.Path]::GetFileName($python).ToLowerInvariant() -eq 'py.exe') {
            & $python -3 -m PyInstaller --noconfirm --workpath $work --distpath $dist $spec
        } else {
            & $python -m PyInstaller --noconfirm --workpath $work --distpath $dist $spec
        }
        if ($LASTEXITCODE -ne 0) { throw "Compute-Node-Build fehlgeschlagen (ExitCode $LASTEXITCODE)" }
    } finally { Pop-Location }
    return $true
}
function Resolve-Plugin([hashtable]$Job) {
    $matches = @(Find-Package $sourceDir $Job.pattern)
    if ($Job.id -eq 'interaktions_ki') {
        $matches = @($matches | Where-Object { $_.Name -eq "MediaHub_Interaktions-KI_v${ExpectedInteractionVersion}.mhaiplugin" })
    }
    if ($matches.Count -eq 0) {
        if (-not (Build-MissingPlugin $Job)) { throw "Paket fehlt; Build nicht freigegeben: $($Job.label)" }
        $matches = @(Find-Package $sourceDir $Job.pattern)
        if ($Job.id -eq 'interaktions_ki') {
            $matches = @($matches | Where-Object { $_.Name -eq "MediaHub_Interaktions-KI_v${ExpectedInteractionVersion}.mhaiplugin" })
        }
    }
    if ($matches.Count -eq 0) { throw "Erwartetes aktuelles Paket fehlt: $($Job.label). Keine aeltere Version als Ersatz verwenden." }
    $chosen = Select-One $matches $Job.label
    Write-Host "ORIGINAL-RELEASE: $($chosen.FullName)" -ForegroundColor Green
    Write-Host "SHA256: $((Get-FileHash -LiteralPath $chosen.FullName -Algorithm SHA256).Hash)"
    return $chosen.FullName
}
function Resolve-Exe {
    # Nur Build-Ausgaben des originalen Node-Repositories, nie die alte Kopie aus 'Quellen'.
    $candidates = @(
        (Join-Path $nodeRepo 'dist\windows_compute_node\MediaHub-Compute-Node.exe'),
        (Join-Path $nodeRepo 'windows_compute_node\dist\windows_compute_node\MediaHub-Compute-Node.exe'),
        (Join-Path $nodeRepo 'windows_compute_node\dist\MediaHub-Compute-Node.exe'),
        (Join-Path $nodeRepo 'dist\MediaHub-Compute-Node.exe')
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    if (@($candidates).Count -eq 0) {
        if (-not (Build-MissingExe)) { throw "Compute-Node-EXE fehlt; Build nicht freigegeben: $nodeRepo" }
        $candidates = @(
            (Join-Path $nodeRepo 'dist\windows_compute_node\MediaHub-Compute-Node.exe'),
            (Join-Path $nodeRepo 'windows_compute_node\dist\windows_compute_node\MediaHub-Compute-Node.exe'),
            (Join-Path $nodeRepo 'windows_compute_node\dist\MediaHub-Compute-Node.exe'),
            (Join-Path $nodeRepo 'dist\MediaHub-Compute-Node.exe')
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
        if (@($candidates).Count -eq 0) { throw 'EXE wurde gebaut, aber nicht an einem erwarteten Original-Buildpfad gefunden.' }
    }
    Write-Host "`n===== COMPUTE-NODE-EXE AUSWAEHLEN =====" -ForegroundColor Cyan
    $candidates = @($candidates | Select-Object -Unique)
    for ($i=0; $i -lt $candidates.Count; $i++) {
        Write-Host ("  {0}. {1}" -f ($i+1),$candidates[$i])
    }
    Write-Host '  M. Anderen EXE-Pfad manuell eingeben'
    while ($true) {
        $answer = (Read-Host 'EXE-Nummer oder M (0 = Abbruch)').Trim()
        if ($answer -eq '0') { throw 'EXE-Auswahl abgebrochen.' }
        if ($answer -match '^(?i:m)$') {
            $manual = (Read-Host 'Vollstaendiger Pfad zur Compute-Node-EXE').Trim().Trim('"')
            if (Test-Path -LiteralPath $manual -PathType Leaf) { $chosen = Get-Item -LiteralPath $manual; break }
            Write-Host 'EXE nicht gefunden.' -ForegroundColor Yellow
            continue
        }
        $number=0
        if ([int]::TryParse($answer,[ref]$number) -and $number -ge 1 -and $number -le $candidates.Count) {
            $chosen=Get-Item -LiteralPath $candidates[$number-1]
            break
        }
        Write-Host 'Bitte eine gueltige Nummer oder M eingeben.' -ForegroundColor Yellow
    }
    $computeVersionFile = Join-Path $nodeRepo 'windows_compute_node\version.py'
    $nodeVersionFile = Join-Path $nodeRepo 'app\version.py'
    if (-not (Test-Path -LiteralPath $computeVersionFile) -or -not (Test-Path -LiteralPath $nodeVersionFile)) {
        throw 'Versionsdateien fehlen; aktuelle EXE nicht sicher zuordenbar.'
    }
    $computeText = [IO.File]::ReadAllText($computeVersionFile)
    $nodeText = [IO.File]::ReadAllText($nodeVersionFile)
    if ($chosen.FullName.StartsWith($nodeRepo + '\',[StringComparison]::OrdinalIgnoreCase) -and
        ($computeText -notmatch [regex]::Escape($ExpectedComputeVersion) -or
         $nodeText -notmatch [regex]::Escape($ExpectedNodeVersion))) {
        throw "Repository-Versionen entsprechen nicht Node v${ExpectedNodeVersion} / Compute v${ExpectedComputeVersion}."
    }
    $portableZip = Join-Path $nodeRepo "release\windows_compute_node\MediaHub-Compute-Node_v${ExpectedComputeVersion}_Windows_x64.zip"
    if (-not (Test-Path -LiteralPath $portableZip -PathType Leaf)) {
        throw "Passendes Windows-Release-Paket fehlt: $portableZip"
    }
    Write-Host "ORIGINAL-NODE: $($chosen.FullName)" -ForegroundColor Green
    Write-Host "SHA256: $((Get-FileHash -LiteralPath $chosen.FullName -Algorithm SHA256).Hash)"
    return $chosen.FullName
}
function Write-Utf8([string]$Path,[string]$Content) {
    [IO.File]::WriteAllText($Path,$Content,(New-Object Text.UTF8Encoding($false)))
}
function Write-Embedded([string]$Path,[string]$Encoded) {
    $bytes=[Convert]::FromBase64String($Encoded)
    $ms=New-Object IO.MemoryStream(,$bytes)
    $gz=New-Object IO.Compression.GZipStream($ms,[IO.Compression.CompressionMode]::Decompress)
    $reader=New-Object IO.StreamReader($gz,[Text.Encoding]::UTF8)
    try { $content=$reader.ReadToEnd() } finally { $reader.Dispose();$gz.Dispose();$ms.Dispose() }
    Write-Utf8 $Path $content
}
# Isolierte Cache-Umgebung nur fuer diesen Testlauf. Kein Zugriff auf Benutzer-Caches.
# Der Produktivbetrieb kann spaeter einen gemeinsamen Cache PRO PLUGIN verwenden.
function Invoke-IsolatedPluginTest([string]$PluginId,[string]$Label,[string]$Script,[string[]]$Arguments) {
    # Nur ALTE, ISOLIERTE Test-Caches dieses Plugins entfernen.
    # Niemals Benutzer-HF-Cache, andere Plugins oder produktive Modelle loeschen.
    if ($PluginId -notin @('gliner','smolvlm2','speech_to_text','interaktions_ki')) { throw "Unbekannte Plugin-Cache-ID: $PluginId" }
    $cacheBase = [IO.Path]::GetFullPath((Join-Path $testRoot '_Isolierte_Modellcaches'))
    $pluginCache = [IO.Path]::GetFullPath((Join-Path $cacheBase $PluginId))
    if (-not $pluginCache.StartsWith($cacheBase.TrimEnd('\') + '\',[StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsicherer Plugin-Cache-Pfad: $pluginCache"
    }
    if (Test-Path -LiteralPath $pluginCache) {
        $cacheInfo = Get-Item -LiteralPath $pluginCache -Force
        if (-not $cacheInfo.PSIsContainer -or ($cacheInfo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Plugin-Cache ist kein sicherer normaler Ordner: $pluginCache"
        }
        Write-Host "Alten isolierten Testcache fuer $PluginId entfernen: $pluginCache" -ForegroundColor Yellow
        Remove-Item -LiteralPath $pluginCache -Recurse -Force
    }
    $safe = $Label -replace '[^A-Za-z0-9_-]','_'
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $cacheRoot = Join-Path $testRoot ("_Isolierte_Modellcaches\${PluginId}\${safe}_${stamp}")
    # Pro Testvariante frischer Cache, damit CPU und GPU unabhaengig eine Nullinstallation beweisen.
    # Unterhalb eines gemeinsamen Plugin-Bereichs; keine fremden Plugin-Caches werden angefasst.
    if (Test-Path -LiteralPath $cacheRoot) { throw "Cache-Testordner bereits vorhanden: $cacheRoot" }
    New-Item -ItemType Directory -Path $cacheRoot -Force | Out-Null
    $names = @('HF_HOME','HF_HUB_CACHE','HUGGINGFACE_HUB_CACHE','TRANSFORMERS_CACHE',
        'SENTENCE_TRANSFORMERS_HOME','TORCH_HOME','XDG_CACHE_HOME','XDG_DATA_HOME',
        'WHISPER_CACHE_DIR','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')
    $original = @{}
    foreach ($name in $names) { $original[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
    try {
        $hf = Join-Path $cacheRoot 'huggingface'
        $hub = Join-Path $hf 'hub'
        [Environment]::SetEnvironmentVariable('HF_HOME',$hf,'Process')
        [Environment]::SetEnvironmentVariable('HF_HUB_CACHE',$hub,'Process')
        [Environment]::SetEnvironmentVariable('HUGGINGFACE_HUB_CACHE',$hub,'Process')
        [Environment]::SetEnvironmentVariable('TRANSFORMERS_CACHE',$hub,'Process')
        [Environment]::SetEnvironmentVariable('SENTENCE_TRANSFORMERS_HOME',(Join-Path $cacheRoot 'sentence_transformers'),'Process')
        [Environment]::SetEnvironmentVariable('TORCH_HOME',(Join-Path $cacheRoot 'torch'),'Process')
        [Environment]::SetEnvironmentVariable('XDG_CACHE_HOME',(Join-Path $cacheRoot 'xdg_cache'),'Process')
        [Environment]::SetEnvironmentVariable('XDG_DATA_HOME',(Join-Path $cacheRoot 'xdg_data'),'Process')
        [Environment]::SetEnvironmentVariable('WHISPER_CACHE_DIR',(Join-Path $cacheRoot 'whisper'),'Process')
        # Installation darf online laden, echter Offline-Test im Einzeltest bleibt unveraendert.
        [Environment]::SetEnvironmentVariable('HF_HUB_OFFLINE','0','Process')
        [Environment]::SetEnvironmentVariable('TRANSFORMERS_OFFLINE','0','Process')
        Write-Host "ISOLIERTER MODELLCACHE: $cacheRoot" -ForegroundColor Cyan
        Write-Host 'Kein Zugriff auf den vorhandenen Benutzer-Hugging-Face-Cache ueber Standardpfade.'
        Run-Test $Label $Script $Arguments
    } finally {
        foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$original[$name],'Process') }
    }
}

# Optionale, datensparsame Diagnose fuer alle Pluginprofile.
# Keine Rohantworten, Secrets, URL-Inhalte oder fremden Fehlermeldungen ausgeben.
function Write-SafeTestDiagnostic([string]$Label,[string]$RunLog,[int]$ExitCode) {
    if (-not $DiagnoseAlle) { return }
    $markers = @(
        @{ key='installation'; regex='(?i)(INSTALLATION|INSTALLIERT|INSTALL:)'; },
        @{ key='modell'; regex='(?i)(MODELL|MODEL|LLAMA)'; },
        @{ key='api_job'; regex='(?i)(API-JOB|CHAT-JOB|/execute|/jobs)'; },
        @{ key='inferenz'; regex='(?i)(INFERENZ|INFERENCE|ECHTER .*CHAT BESTANDEN)'; },
        @{ key='backend'; regex='(?i)(BACKEND TECHNISCH BESTAETIGT|backend_verified|BACKEND-NACHWEIS)'; },
        @{ key='tool_calling'; regex='(?i)(ECHTES NATIVES TOOL-CALLING BESTANDEN|IOBROKER: Tool-Calling-Test bestanden)'; },
        @{ key='bereinigung'; regex='(?i)(Port 876[6-9] wieder freigegeben|BEREINIGUNG)'; }
    )
    $lines = @()
    if (Test-Path -LiteralPath $RunLog) {
        $lines = @(Get-Content -LiteralPath $RunLog -ErrorAction SilentlyContinue)
    }
    $fields = [ordered]@{ plugin=$Label; exitcode=$ExitCode; protokoll_vorhanden=(Test-Path -LiteralPath $RunLog) }
    foreach ($marker in $markers) {
        $found = $false
        foreach ($line in $lines) { if ($line -match $marker.regex) { $found=$true; break } }
        $fields[$marker.key + '_marker'] = $found
    }
    $json = ConvertTo-Json -InputObject $fields -Compress -Depth 3
    $diag = 'DIAG_ALLE ' + $json
    Write-Host $diag -ForegroundColor Yellow
    Add-Content -LiteralPath $RunLog -Value $diag -Encoding UTF8
    Write-Host 'DIAG_ALLE: Marker sind nur Hinweise, kein eigenstaendiger Erfolgsnachweis.' -ForegroundColor Yellow
}

function Run-Test([string]$Label,[string]$Script,[string[]]$Arguments) {
    Write-Host "`n========== $Label ==========" -ForegroundColor Cyan
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $safeLabel=$Label -replace '[^A-Za-z0-9_-]','_'
    $runLog=Join-Path $testRoot ("Startprotokoll_${safeLabel}_${stamp}.txt")
    Write-Host "Startprotokoll: $runLog"
    $savedEap=$ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script @Arguments 2>&1 | ForEach-Object { $line=($_ | Out-String -Width 4096).TrimEnd(); if($line) { Write-Host $line; Add-Content -LiteralPath $runLog -Value $line -Encoding UTF8 } }
    } finally { $ErrorActionPreference=$savedEap }
    $childExit=$LASTEXITCODE
    Write-SafeTestDiagnostic $Label $runLog $childExit
    if ($childExit -ne 0) { throw "$Label FEHLGESCHLAGEN (ExitCode $childExit). Protokoll: $runLog" }

    # ExitCode 0 allein beweist keinen erfolgreichen Modell- und Inferenztest.
    # Nur die eindeutige Erfolgsmeldung des jeweiligen Originaltests gilt.
    $logText = [IO.File]::ReadAllText($runLog)
    if ($Label -like 'Interaktions-KI *') {
        $expectedMode = if ($Label -match 'gpu$') { 'cuda' } else { 'cpu' }
        if (-not $logText.Contains("ECHTER INTERAKTIONS-KI-CHAT BESTANDEN: $expectedMode")) { throw "${Label}: Chat oder Backend nicht nachgewiesen. Protokoll: $runLog" }
        if (-not $logText.Contains("ECHTES NATIVES TOOL-CALLING BESTANDEN: $expectedMode")) { throw "${Label}: Native Node-/HTTPS-Werkzeugrunde nicht nachgewiesen. Protokoll: $runLog" }
    } elseif ($Label -like 'SmolVLM2 *') {
        $expectedMode = if ($Label -match 'gpu$') { 'GPU' } else { 'CPU' }
        $success = "========== $expectedMode INSTALLATION + MODELL + ECHTE VIDEO-INFERENZ BESTANDEN =========="
        if (-not $logText.Contains($success)) {
            throw "${Label}: Kein Nachweis fuer Installation, Modell UND Video-Inferenz. Protokoll: $runLog"
        }
    } elseif ($Label -like 'GLiNER *') {
        $expectedMode = if ($Label -match 'cuda$') { 'CUDA' } else { 'CPU' }
        $success = "===== $expectedMode : INSTALLATION, INFERENZ UND API-JOB BESTANDEN ====="
        if (-not $logText.Contains($success)) {
            throw "${Label}: Kein Nachweis fuer Installation, echte Inferenz UND API-Job. Protokoll: $runLog"
        }
    } elseif ($Label -like 'Speech *') {
        $expectedMode = if ($Label -match 'gpu$') { 'gpu; Backend cuda' } else { 'cpu; Backend cpu' }
        if (-not $logText.Contains("ECHTER SPEECH-API-JOB BESTANDEN: $expectedMode")) { throw "${Label}: echter API-Job/Backend nicht bestaetigt. Protokoll: $runLog" }
    } else {
        throw "Unbekannter Testtyp: $Label"
    }
    Write-Host "${Label}: BESTANDEN (Installations- und Inferenznachweis im Protokoll)." -ForegroundColor Green
}

# Medien sind bewusst unabhaengig von der Plugin-Installation. Keine Abhaengigkeit
# zwischen GLiNER, Speech und SmolVLM2; keine Downloads fuer die Testmedien.
function Get-TestMedia([string]$Kind,[string]$PluginPackage,[string]$MediaRoot) {
    New-Item -ItemType Directory -Path $MediaRoot -Force | Out-Null
    $txt=Join-Path $MediaRoot 'Testtext.txt'
    $wav=Join-Path $MediaRoot 'Testaudio.wav'
    $vid=Join-Path $MediaRoot 'Testvideo.mp4'
    $png=Join-Path $MediaRoot 'Testbild.png'
    $sentence='Anna works at Microsoft in Berlin. Peter visits Hamburg tomorrow.'
    if (-not (Test-Path -LiteralPath $txt -PathType Leaf)) { Write-Utf8 $txt $sentence }
    if ($Kind -eq 'gliner') { return @{text=$txt} }
    if ($Kind -eq 'speech_to_text' -or $Kind -eq 'smolvlm2') {
        if (-not (Test-Path -LiteralPath $wav -PathType Leaf)) {
            try {
                Add-Type -AssemblyName System.Speech -ErrorAction Stop
                $speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer
                try {
                    $speaker.SetOutputToWaveFile($wav)
                    $speaker.Speak($sentence)
                } finally { $speaker.Dispose() }
            } catch {
                if (Test-Path -LiteralPath $wav) { Remove-Item -LiteralPath $wav -Force }
                throw "Windows-Sprachausgabe konnte keine WAV-Testdatei erzeugen: $_"
            }
        }
        if ((Get-Item -LiteralPath $wav).Length -lt 2048) { throw 'WAV-Datei ist zu klein oder leer.' }
        if ($Kind -eq 'speech_to_text') { return @{audio=$wav;text=$txt} }
    }
    # FFmpeg zuerst aus dem bereits ausgewaehlten ORIGINAL-SmolVLM2-Paket
    # extrahieren, genauso wie beim erfolgreichen SmolVLM2-Einzeltest.
    $ffDir=Join-Path $MediaRoot 'ffmpeg_tool'
    $ff=Join-Path $ffDir 'ffmpeg.exe'
    if (-not (Test-Path -LiteralPath $ff -PathType Leaf)) {
        Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
        $archive=[IO.Compression.ZipFile]::OpenRead($PluginPackage)
        try {
            $entry=$archive.Entries | Where-Object { $_.FullName -eq 'mediahub.smolvlm2/tools/ffmpeg/ffmpeg.exe' } | Select-Object -First 1
            if (-not $entry) { throw 'FFmpeg ist im SmolVLM2-Paket nicht enthalten; keine stillschweigende externe Installation.' }
            New-Item -ItemType Directory -Path $ffDir -Force | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$ff,$false)
        } finally { $archive.Dispose() }
    }
    if (-not (Test-Path -LiteralPath $vid -PathType Leaf)) {
        & $ff -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=320x240:rate=2:duration=4' -i $wav -map '0:v:0' -map '1:a:0' -c:v mpeg4 -q:v 5 -c:a aac -shortest $vid
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $vid -PathType Leaf)) { throw 'Testvideo-Erzeugung fehlgeschlagen.' }
    }
    if (-not (Test-Path -LiteralPath $png -PathType Leaf)) {
        & $ff -hide_banner -loglevel error -y -i $vid -frames:v 1 $png
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $png -PathType Leaf)) { throw 'Testbild-Erzeugung fehlgeschlagen.' }
    }
    foreach ($f in @($txt,$wav,$vid,$png)) {
        if (-not (Test-Path -LiteralPath $f -PathType Leaf) -or (Get-Item -LiteralPath $f).Length -eq 0) { throw "Testmedium ungueltig: $f" }
        Write-Host "TESTMEDIUM $f SHA256=$((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash)"
    }
    return @{video=$vid;audio=$wav;image=$png;text=$txt}
}

Write-Host "===== MEDIAHUB NULLTEST v$ProgrammVersion =====" -ForegroundColor Cyan
Write-Host "Quellen: $sourceDir"
Write-Host "Erwartet: AI-Node v$ExpectedNodeVersion; Compute Node v$ExpectedComputeVersion; Interaktions-KI v$ExpectedInteractionVersion"
Write-Host "Tests:   $testRoot"
Write-Host 'Fehlende Pakete/EXE koennen nach JA-Abfrage mit den Original-Buildwerkzeugen gebaut werden. Kein Git/Release.'
if (Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8766 ist belegt. Fremde Node wird nicht beendet.' }
if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) {
    Write-Host "Release-Ordner noch nicht vorhanden: $sourceDir" -ForegroundColor Yellow
    if (-not (Test-Path -LiteralPath $pluginRepo -PathType Container)) { throw "Plugin-Repository fehlt: $pluginRepo" }
}
$selected=@{}
foreach ($job in $jobs) {
    if ($DiagnosePause -and $job.id -ne 'interaktions_ki') { continue }
    if ($job.id -ne 'python_runtime' -and (Confirm "$($job.label) fuer Test bereitstellen?")) { $selected[$job.id]=Resolve-Plugin $job }
}
if ($selected.Count -eq 0) { Write-Host 'Kein Plugin ausgewaehlt.'; exit 0 }
$selected['python_runtime'] = Resolve-Plugin ($jobs | Where-Object { $_.id -eq 'python_runtime' } | Select-Object -First 1)
$exe=Resolve-Exe
Write-Host "EXE: $exe"
$queue=@()
foreach ($id in @('gliner','smolvlm2','speech_to_text','interaktions_ki')) {
    if (-not $selected.ContainsKey($id)) { continue }
    foreach ($variantMode in $(if ($Mode -eq 'all') { @('cpu','gpu') } else { @($Mode) })) {
        $file=[IO.Path]::GetFileName($selected[$id])
        $version=([regex]::Match($file,'_v([^_]+)\.mhaiplugin$')).Groups[1].Value
        if (-not $version) { throw "Paketversion unlesbar: $file" }
        $pluginRoot = Join-Path $testRoot ("${id}_v${version}")
        $folder = if ($id -eq 'smolvlm2') { Join-Path (Join-Path $pluginRoot ("smolvlm2_${variantMode}_v${version}")) $variantMode }
                  elseif ($id -eq 'interaktions_ki') { Join-Path $pluginRoot ("interaktions_ki_${variantMode}_v${version}_" + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
                  elseif ($id -eq 'speech_to_text') { Join-Path $pluginRoot ("speech_to_text_${variantMode}_v${version}_cudafix_" + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
                  else { Join-Path $pluginRoot ("gliner_${variantMode}_v${version}") }
        if (Test-Path -LiteralPath $folder) {
            $installed = (Test-Path -LiteralPath (Join-Path $folder 'runtime\private_python')) -or
                         (Test-Path -LiteralPath (Join-Path $folder 'runtime\plugin_runtimes')) -or
                         (Test-Path -LiteralPath (Join-Path (Join-Path $folder $variantMode) 'runtime\private_python')) -or
                         (Test-Path -LiteralPath (Join-Path (Join-Path $folder $variantMode) 'runtime\plugin_runtimes'))
            if ($installed) { Write-Host "Installation vorhanden, wird NICHT ueberschrieben: $folder" -ForegroundColor Yellow; continue }
            Write-Host "Vorbereiteter Testordner kann weiterverwendet werden: $folder" -ForegroundColor Yellow
        }
        if (Confirm "${id} ${variantMode} v${version} als FRISCHEN Nulltest vorbereiten?") {
            $queue+= [pscustomobject]@{id=$id;mode=$variantMode;version=$version;folder=$folder;pluginRoot=$pluginRoot;pkg=$selected[$id]}
        }
    }
}
if ($queue.Count -eq 0) { Write-Host 'Keine neuen Varianten ausgewaehlt.'; exit 0 }
$plannedKeys = @($queue | ForEach-Object { $_.id + '/' + $_.mode })
if (@($plannedKeys | Select-Object -Unique).Count -ne $queue.Count) { throw 'Doppelte CPU-/GPU-Variante in der Warteschlange.' }
Write-Host ('WARTESCHLANGE: ' + $queue.Count + ' bestaetigte Varianten: ' + ($plannedKeys -join ', ')) -ForegroundColor Cyan
Write-Host ('Varianten in Warteschlange: ' + (($queue | ForEach-Object { $_.id + ' ' + $_.mode }) -join ', ')) -ForegroundColor Cyan
# Vor dem Anlegen alle geplanten Verzeichnisse und zentralen Dateien pruefen.
$depthItems = @()
foreach ($planned in @($testRoot,$internal,$pkgDir)) { $depthItems += Test-PathDepth $planned 'Ordner' }
foreach ($item in $queue) {
    $stage = Join-Path $item.pluginRoot 'Quellen'
    foreach ($planned in @($item.pluginRoot,$item.folder,$stage,(Join-Path $item.folder 'runtime'),(Join-Path $item.pluginRoot 'Testmedien'))) {
        $depthItems += Test-PathDepth $planned 'Ordner'
    }
    foreach ($planned in @((Join-Path $stage ([IO.Path]::GetFileName($item.pkg))),
                            (Join-Path $stage ([IO.Path]::GetFileName($selected['python_runtime']))),
                            (Join-Path $stage 'MediaHub-Compute-Node.exe'))) {
        $depthItems += Test-PathDepth $planned 'Datei'
    }
}
Show-PathDepthReport $depthItems
Write-Host 'Hinweis: Speech-Test erzeugt den endgueltigen Ordnernamen erst beim Start; angezeigte Tiefe ist eine Prognose.' -ForegroundColor Yellow

Write-Host "`nGeplante neue Testordner:" -ForegroundColor Cyan
$queue | ForEach-Object { Write-Host "  $($_.folder)" }
if (-not (Confirm 'Diese Testordner jetzt erstellen und Pakete bereitstellen?')) { exit 2 }
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null
New-Item -ItemType Directory -Path $internal -Force | Out-Null
# Pakete und EXE werden unten je Plugin-Version separat kopiert.
foreach ($item in $queue) {
    # Jede Plugin-Version hat ihren eigenen Bereich mit getrennten CPU-/GPU-Laufzeiten.
    # Originale bleiben unveraendert; Kopien liegen pro Plugin-Version im Quellen-Ordner.
    $staging = Join-Path $item.pluginRoot 'Quellen'
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    $item | Add-Member -NotePropertyName stagedPkg -NotePropertyValue (Join-Path $staging ([IO.Path]::GetFileName($item.pkg)))
    $item | Add-Member -NotePropertyName stagedPython -NotePropertyValue (Join-Path $staging ([IO.Path]::GetFileName($selected['python_runtime'])))
    $item | Add-Member -NotePropertyName stagedExe -NotePropertyValue (Join-Path $staging 'MediaHub-Compute-Node.exe')
    Copy-Safely $item.pkg $item.stagedPkg
    Copy-Safely $selected['python_runtime'] $item.stagedPython
    Copy-Safely $exe $item.stagedExe
    $expectedExeHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    $actualExeHash = (Get-FileHash -LiteralPath $item.stagedExe -Algorithm SHA256).Hash
    if ($actualExeHash -ne $expectedExeHash) {
        throw "Falsche Compute-Node-EXE im Test-Staging: $($item.stagedExe). Erwartet $expectedExeHash, gefunden $actualExeHash."
    }
    if ($item.id -eq 'smolvlm2') {
        Copy-Safely $item.stagedExe (Join-Path $item.pluginRoot 'Quellen\MediaHub-Compute-Node.exe')
    }
    if ($item.id -eq 'interaktions_ki') {
        # Untertest erwartet einen vorhandenen, aber noch leeren Testordner.
        if (Test-Path -LiteralPath $item.folder) { throw "Interaktions-KI-Testordner bereits vorhanden: $($item.folder)" }
        New-Item -ItemType Directory -Path $item.folder -ErrorAction Stop | Out-Null
        if (-not (Test-Path -LiteralPath $item.folder -PathType Container)) { throw "Testordner konnte nicht angelegt werden: $($item.folder)" }
        Write-Host "GRUEN: Interaktions-KI-Testordner angelegt: $($item.folder)" -ForegroundColor Green
    }
    if ($item.id -eq 'gliner') {
        New-Item -ItemType Directory -Path $item.folder -Force | Out-Null

        New-Item -ItemType Directory -Path (Join-Path $item.folder 'runtime') -Force | Out-Null
        Copy-Item -LiteralPath $item.stagedExe -Destination (Join-Path $item.folder 'MediaHub-Compute-Node.exe') -ErrorAction Stop
        $settings=@{schema_version=1;node_name="Nulltest-$($item.id)-$($item.mode)";listen_host='127.0.0.1';listen_port=8766;execution=@{default_mode='auto';cpu_threads='auto';gpu_device='auto'};connection=@{require_authentication=$false;allow_remote_jobs=$false}}
        $settingsFile=Join-Path $item.folder 'runtime\settings.json'
        if (-not (Test-Path -LiteralPath $settingsFile)) { Write-Utf8 $settingsFile ($settings | ConvertTo-Json -Depth 10) }
    }
    Write-Host "Quellen bereitgestellt fuer $($item.id) $($item.mode); geplanter Testpfad: $($item.folder)" -ForegroundColor Green
}
Write-Embedded (Join-Path $internal 'web_test_setup.py') 'H4sIAAAAAAAC/41STYvbMBC9+1cIehibKt5uSpeS4MNuG9hCGpYmobDbYJR4YquxJaMZ52NL/3ulxIEeeqjAwjPSvDfvad6IWef8V9eMxIPnrlSmpEIxmrF4Rsd6q3eKxUG7QhSd21Tik23ajlHMbIGCsF4TC3Sv2JWcRrpprWNhSQo6+e0nWSNFpaiq9drncOOQKdo624hWcciKvubJh5HrDOsGsxDEHiFVrty/3K6ScajN+uMb8EHnNJ/gnE+bXaFd3CqHhilbuA4lHjVxbnfnKIk6QmeUR7aUotlrZ80LfJ18/nL/uHzIZ8vpdDGZL/Lvk4d8OZ98g9XY90d0sK74j5Kn+/kcVhGpmrNeY8p2hyZfn7yx8fthEhW69BZnvRdpu94V22FeNWoTA1Vq+OEO5JXS8228vTF0vB18hEQGZHn3Lqwk8vgFZb+ANhU2Kt+jI20NjG4lXGXC6PonQdWl9V5VDYygZ73ygWZ0in01wegCLyFwwSjsaYXHOJEQeobRRcAl9zuKvc4bOOA6D+1437WqKQ3vDUl68HyYMx45Dpm06JqW4nPfUptwOxsmb+GHAXlWqk2ZXbVGrdOGY/jnUA4efSt+3IjRn47FYjof/DWm/RyKQl/mM/VwfwAAv2Uj4wIAAA=='
Write-Embedded (Join-Path $internal 'GLiNER_CPU_CUDA.ps1') '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'
Write-Embedded (Join-Path $internal 'SmolVLM2_CPU_GPU.ps1') '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'
Write-Embedded (Join-Path $internal 'gliner_echter_modelltest.py') 'H4sIAGYH5WoC/41VbW/bNhD+rl/B+Qtl1NLSLB2wAP6QNt46NHGM1AU2FIXASCeLC01pJOXYKPrfd0eKjrPaw4wgko53x+eeexuNRve9tqzVasd6XYFhrgFWG7ANSqS2TigFFeuM3AgHbLFzTavZk3QNy37PR6NRItddaxwTZtUJYyF+/2VbHd9bm9SmXbNOuEbJBzaIF/gZVax0e1O7s0nSseneZ35lVv0atFvQl0nHSZeLqirEIE55lpleO7kGPmEG/u6lgWq6ND0cU+1MW0tFqmXTyhLsNOVl1+M3L/tK8PF3PgSC6XKPhTxZRGDa1qGUYkhFPtw+zpG5Vm0AFWDbQemQuynzuj8yPrBYdJ5FTqIyvGc/5a/P89dn2fbni0xYZ4TKzs/O35xdnP3i9YJaDlvgiShdL1S8HNkicdk78aBeIJA1G1R/mLII5/n8MmH4M0JaYPcB/8yY1qQ1n/2xnN3PZ/ds8efy/d38kn0Njr6Rp6/R1TeONLjD+FS/kroYyLAe+EpJDYYnnSgfxQosqQflQcCTDehNQQWwPyOJt76RD/5Jp9mzRd0aVmF5sjTKJmzvZQgMo69yaYtKmhgr/UiDKoKedIRcp9V4HGsvwI1frjVlk2DaqHBeZu8SyyWQMmG16m0Tyy0oBz/Fuq16BaQbBHlRUOkVxVEjf92Bjf/+PyYbMFYGTNFmEJ0wozovxEZIRUXzbEdyIm1/lI5f2uM4aJ98UX8m5iL9z1U1zknBkB0p7LNyROOLz2MI1yczcDRgGXJGMwNvI1++3IP6npTxEb8x/RqrUuhdSi5ynGTGWRpc6Za9wpGUW+jGjBBs6fIhsINKOdIZsTE+ssXVh9nyknF0Re5Ds+XDZGHT6TBK8P7K4zhJ78ku5O8+XV+xp95UgLVtlNArN2HSYkwPOKe1LBtHB3UPqwdh+DEIONQ8Av7KvxIQDPW7EonEed1wOpx5xHipN523Gv4D7uJTtgSE1wjHCHu22C3JV1wjEoxDlH4ThEzHRfDbjcRhk2BqQVG/7ueAlxzOkWLdKyezDc5KHvRRN5jn5LjoDODwRNXKd/beJZajakuhfNnYghbeUNHRi3/mrk2HzJ1IKOKBwOw4sbhQQJc0t/iVXoES7BbMI7rbSD9f2FtMHDKOf3elaylvONUvcp6gpXTSj8NwMQKvZOmKeJBG5xP2mXeYDVwYuKAoCCfDe4XTiH/BdmloX7eqmp7l52/2PT7DAoGBnGyGsLTu9Yp6nXZzXvXrzqbxugkDbXuD682WUk5/FRjmhFVQCyR8ilT+aw4M7YVhUnIR5oEnhUU6ZthYpBHFpwsnIEQrqLFCgD0Cpo8hj0ITA2xGHgTgKz/VZvuJr2Hr0oFQYcQarYyl0VDBBjd97nYd0A47NDuF65bcKKYE9LUb+k30ta9t/szyu/c4Etjt3fXs5mY5+7hkb/Hf1fx6NvcrIoJ9Sd8/fG7pt3kJAAA='

Write-Embedded (Join-Path $internal 'Speech_CPU_CUDA.ps1') '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'

if ($selected.ContainsKey('interaktions_ki')) {
    Write-Embedded (Join-Path $internal 'native_tool_calling_probe.py') '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'
    Write-Embedded (Join-Path $internal 'Interaktions_KI_CPU_CUDA.ps1') 'H4sIAAAAAAAC/+1dbVfburL+zq/Qzc46ThYkvJS2lKyss1MIkEKBTUJpy+7hOImSuDi2aztQSvnv9xlJtuWXhNJ230+3e+0WbGk0Go1G86axZ/rmtLLE8OfynWlbQzPkXR5WjIE3M1aMMf6ufroMQt9yxp/Kb90hZ00mX8pOpwSAh9yvvDUd9Hb9u2Y59Gdc69bjQbjn2kPuP6FT+ys/NcPJE3qc2rOx5Zyag2tzzJ/S7y6cuJl+wa0VDiafyruWOXbcAKjMAr5UXRrYwVK57fuu3xqEFnr5fMR97gwEXbqh6xlL5VPfHfs8CDIvLZs7oX234zqh5cy4sWSNWCU9AqsBSybpXHO4pHSV3bNw4ru3zEg3toKQOTOfjWbcZzun5+zG9cc84BPu1A32sFQOBr7lhdtDvdeu6/BmeWTamM9o5ohZsAvTCmtp4PeCEIRizXFDlsXT9dlc8OKt7KWaOGJCWh96UD8wg/ZXK+RDmqHPw5nvAGsadgHmtHiizYWPrrUDF0Qwdjut/eOTbvu0dd5tb7Ndi4jj2hb3Q86OafC+za1+yMzr0LppsNZph81A6T3L57embbNb7g+5wxx3MGGONZiErI+VsxxrHIKUtT3X52PfRZcd18Y0PnDbdm+zaJSI0S0nCAHRJLpuM433SzmsLzh+9jk7xZSwFGMgYDkMo/Ip+3ZLLx126gK17gTj1fY4QGOlQQus+ASMVWeH1Jp9nI1NZxzQ5nXo9Zj3iQUkKT3f7fPmG9dyarShWPm02xXUPXOxQoYDTG/4Vei69tUAiGNLXIkude/OyKJcMTyxWVjtNSsZbFlBxw9GidVqfewhDrKCa/EbrTH+qpkzjFqr+dzjoUVkCdi6Uf0l0EOs2yCsgcxTcw7ooatYWBDBdALQsXnGzaEi/h54wxqzqRUyLA6L2Pvf7E2LlkCQUO6sG9e2saYY3Rpz9lrxBdZLkucBnBRaNrayHITVpiZkBzP+U/m3tf3ZrJaBETajI4Vn2ZnZ9lLZp05TeqCtTMIszFANIE7w4Cxufdl2bizfdaaQJZ+2t/d5qD14Z/qWCU6vGG/b2BIH56+vdk7enp732ldn58e9zts2ZDqk0wDCCUgRZCXSnwr26Kj1tnX19mQ3D7E1C0Fg0w9/GmzrvHfS7bXOemnYEQs0hVRSQpJ/YfKUgggxBrOhCcHHuE0CTEpPSJRYzLWCAKteKUMEDwW7rCRHGwaB+CcwicyL2yUiOGqIUTTAXfOG194ErlNJThU6vMo4U2cC6GXnpL6HEwBUEEzfsu0e/wpcRLuKbMi+Mwx5Axx7rgDHarvcA2c8X6uuVI75be2k/xmMz6hr/by3t9V2Bu4Q41WkRK9WqzpaZ/zLDCyVIHXu2/qUsd+GTQOrYqxcTsxgEtJyfCofYJdwP2j+ef+QtCbkmwbRWXD9H+yg1zuFTJrY4Fbaj9chiR6xmc544GEvcmbjNHIamhBjz+vr7Np0HBZARve5pYB1nBv3mtfQMZRosZp2yjI6WBnogY2LaQIsHavstTu8Y6bzjWNfOnUp7Xw55eZl9w7Cclo/5mH9IAy9C95X1MAK7PgcorJC5KimutUVTRRt6j333PO4D+yIV52wkmnew6Z0Z2Hz5cYa/Um/JGEj1nphq0POvZYNERwdyqm3rcEADNA0TM+zrYE4VFY/gxBS9IxwLJmDSaV8ze/o6IhWDkDvAuK6GI56cUktPzXjRU09VmevNaqIxa7q8rN/F/KgqTExTQ48/Jqeq/ZJ62hUUnWw0Xt3Hk9PwR2EPKwBC25Ojbn9jrgzDidNOXhd/pY0lr2bcSewsVrhrnhTSRAK/TsihuxRF2tSkVBX1lZS4LF92MhycA7qPXYt8HPAK1VFIilhiFARs5IYOoXYM1JUT89jLVJufLU9mvIsiDHUCRG1SM1OPqykKE0L2NREA5ZIzv9MvKrEsHQQEYVWLoUkiaQI1pWESo5wfWy0phpLsHXPbTvDSoZY6n2WWIqnIp7b3u4Ex5j2iX8xwTp0PXNAi4ERqtV7pQQKuiS91VPZKpGRe747FVKyqhZlIM5dfedj17e/0g4C033SCXzL+83yVT1+qbOVGc6CpiE1KyHkWk546/qhxqhDHpqWDXGoz5CA1iMK67tHh3tp4SRMtcRy0ZsdHGfZHpLBU40LFjHVi/CQHav3P8Idsu0cPmhg/e+jyRas/4Na/fvc2j8kq5f8JE/QEtE0ogcdASzaRSSPWYN1uY/lNSXRtyNi40VZkjg6qktq2RMWpMlH7C6mr4iWoAVsHpaEmnJkOqQINp+qonSOe+2z1mGvc3LcvTrsXB21jq8OoK7k9KCeHeyAS395gN5R92qnfVY4AOT8b4F/2P6QBw+xcw596ckDHJ8fHfXa3d7VRfv1Feyxs0LQp2YQ/Bro01a3mwY9UubcMWz+pvGWw3w8mPWhXMBsIssPzFA77IhN3WVYOCM2kaOeJ7cOH0YncfQSTCcIoVT35CnNAUw6zLyxTafjqWexLkZzrp2CoytSBNCPmt172YcB9unPCkhQg+Tq7ZxCyjlc9q0duTDNqAcT/ViNZAZnR/AAQA9Kq0oZN0NKIRR2fgaJFTk0HC4ehuPDFfmqywfQfoPmxvNIlEHbqJSt5lqjbLGaDVRUE/y+vCwV50olniZTM6SjMYadSHgy4x8aXbITal3ocx7mJMGxdSUyIrH/GMwlbYJEPuzszunNpsK6HLgwG0JdCGoHRFe8DNS/lcuCV63hkJw5e+bUsu/o+CJuQgMs/PXK5VxYpPSg9e7YJ/Fa0Ax8G7oD11YNz4detUgVkOjXFTdUjPW6+M9Y2dx8pikClhdrdalZdE4hqU9dsaQKlGCm6Gk1ml9OmEbNs+c5CVnLE/6d2NBdX/u7/n391cbf9fUXW/TjS/xYWb98UXv16fvG5Rr98+xybf1T9e96lXQkdRTIQ9bzrRtiZ7Fq5mwEdZ+cdf4QHpeQb9PkSimWwAMS4/GqK+sh8ubInVBJOzTN4RDCwudT94brPk3ZOLFz6FDoeBHPl83h1HKaICkfzKA33mHZLGdgeaZdv7CcoXsbxA8+LWjUgXcJHoo7KeR2Zj7sF1gT1Xon6DhnLoTcgs6vZ5Ydymbo3yKMsPF98mYqe2QwHTZpXZQMEOooTVjXQkq0A8ASEZXOZjbsZ1pd27wjicmMlAA16KXPIwr3yfvFamqEFvm/WC3iYQZ5pUuprZcvXqnfFXsBuKQswJ5hEWABqxeiVXfWd3goAI4gwOASkyyRtwK/s5MZRCRka0nTxfV5KhH6hHkWDHImGCUPJ9tUIRHvDMEvJAz/xTyyegOyeuv8K7oeu9Hs8KMjD6UBOd9YbcedTsnzW/pvsXO5KV3LDbHSpYYY6ajV7bXfd3o7cMIIZ/FaNdpWEcq18r2EhH0NQx2+4cHEhurklB4UyhnalU1/HDRLi1CFX34wE9jBvzq4Y6/vPJyCyRT++0Nz+G+plAzqNeU5oE5yuFsxsvCIGWkaYqla/nhGygEdfRJdVnvH/T6Di6yFn+lI7k18OAnprEup516dvM07kW99LRFDeXpts9Q2G8HnNzbhjYRiekvuBvC4S54O5f+oEGTST5MxqlUlsx7080kcZTpHVeYJHh8v4YKpPMrNKWZ+RBeI2VRAx6ECv6IgxnpyMgvdJ7JUm7Ll5dqnBpap7GNnZBCi/Y71Aoc0ymZhi+gAFY3SJ3vZh81BOp4yoXvQCiC0RBSEXiYCSLxWUkhvoUs8IZTUS7XyCXn9eszS6thSMuZ75T/fV6oblTL+jiHH3bz4nGY1eFj+rBgQdThIXhjVOQN59UQOCrRIGOYBm/WUeBQqTcQChXDNelpuCtia8ARCOU5LvF66D9BKTjuh1xrGCtP8ltDLEz8fOSCal4940azELRa7xNbJ2dUQj7IuLvlUrBY5i8+4dOfrDjDiUcKNrDjztllonpItrPxP1HTZ2DaWBfpVOUDk3DIwyMT1rW/C92R8ahqvzcAaMGP5UnkSALDn4iF/sdkVZKjQqNWHJc0HApoLb0zaEyMs5EiFF0oW2mkWvW4hY7/ZsRVKkJW/osBRQdPXvBOJV+Fe4lH07udQeWgIGZgSUiSna7CEROAsigNWcgG9SGQ8KB/uiQO9MZyQPiflOFwLnPmIMmF7m2HqlQgQ4HGfelhoSj4upXHZthJ7O9a0Q9E0CqBCFXq2cRWfENljWDHgtePeOugt56/HGjtDcMVgYtnYPNSiKEjk8Fu8IQQgxC4mOLYii+G+IkGzGkwUeCMQZ5JDXNURYYaMVYhhFLXPBbUW9IrbVx8SLT7253rCmwt8sOASxHJT9fWSvsmE6HXZi5yTt3iKfYnukYQfhzjuZGTb9H3zTjhwwflggRhGdakAhfilRqaB1F6bjyyRlPesFKPbFOdjMvPS4sMqdXarMVV8XP1WFxIIfXeFqkgS1Es9q94LVo5R6gyZjoGI6w4eOTMf0gpebhdoUeyC0dIs+IQBhedN703qDHrTUDC38Kf6PVKEH4QguU+HzqmT8kFkHQC0r1uelQoLzTPyIcalfZ8wQLHRnlquOfRR6paQK8hVQOCGQrB9jqgeJ09fumOsSZUedIf0fXnCTRv+dHUSsRLhvyoflho0vPy5rlyM4qB0r41YXqXopcgt8yugxHqzKGVAywNAEgAZnIlpLiOJTLkmSFWtHVEwH+e+iOSq7BUm3pGFz464OarGI4g1qLXft4ViHqpY/WNQUxkuedgZPxfew35/2gB6Kkx+APm6pqLRPwFfC3AnwHekcMRhz0rv3Ck7MGdeSAcC8YgkP2XwCI0GzjY0lGMWZFdE40vpOw8LFVqHAleKAuv8K1R9ShdR6x002DV8E+wcaQA+rCY8Qz7Adty3pAVBu7WPlEswsq5xyE1n2PrDmY+DfYgIJ1ZjBuNFcRQyIVwonxYAMg72n0Euy8yTuoInHSKt/gTpBmNrDByICkgK+Qr8KS9ELcHAv/NCZBmZ3uROWiKuh/SQwJYpC5TL0ouP1IgqQhoIdV8er8pii/IuFloO8eqrAVIZNoLQehKK6ZCZWcgacmkec3NCZ37xJC8n4Rd37HObj8MGg9k2HSra31r+MN7SQuD8LGIvfxaxlxnEfCYSWGqBCHj8KIaJNxQgt3T4WxHz5saBeokVw0H9OMRXOsRXcyFKxt/Vgf7B2sS8UQ9s3gnYi+PRGR9zm435xKVR5RSHYGY6vMRGJ9eSytCaOQBA6U2RPpjx0MOhIDerM25WfrN5nFeXtMOsAAHdvaYndh10ji/ane62olKEnC/IkKNPQ678LSe6UuSL1p7oRMlo6OGS2+axNDR5jJGLrwPXLxN/C+kqTWjkPbJaSvpFukjiTxMQdlzvToEoPtB2RY6bULFYZU7uUhR5qemnnXDgRP5KEzly7ljPSovQMjxxyF158hC6Uk2NH56f6vDE+WVOPn2WEcTF/dNH89z+5YCHxDqUXYNl5VPzivRwtGuuN0jtuXIoeFXKnuXRVqlFaVClhi3Ez9WEopjG+sbL+hr+Wzei5x72cJPEYYNHLjuMOeQjc2aHV1OhHlZEDkM6kepe/PNAnsF7kUH1UG3gnyuoSDCo4RugU8xooNHVkN9Y5NgTTx4ag1hiYiBKXMDSXFH2H/m+ZeZH5AEwiXGvfOHQuPrs9gP14qGB4NnVBK4GIpBAUo0np2mowHKccJXiwZiHIiLXRa5MNaG6ElTnjgXdkSG1h6EPo1OQxlphDllFFJCAGMAGu6VNzSBL8DuOYDbwuXDkA9W0dJIhPy36pBwiEFKJY39HO7TrZxjUnR7PppAH+xCSws+YeFW0WFC5Pxvp4SvKV7n8xDY2GwRf84KgHbk+BODmAt8Gtav3fGtKQXyjaVThQ8AckYdhLMO19VV/sIoHd4ZyhcTBITFwElVPkSKKlhrTSU1wLLwyEqc6HFXS5KisraxvVLPdknCqbL9s/A98NPsza4hJgAD0UwWYu2oixrGSJ5kwcvcnItQZ7PWw8i+PIAPVBRPNjgLDxQZPNueIVfS8IopegZtnXpyfq3oJ7xiC18bBZtBpyT87q5vr3d6Hm/7b1zuvltcHHT6x+ofh81nX493Nt8ez/VeTnX3vw9Tt7/Y/vDnb/PBl9vWN+fbj843jo9VnM/trp835l8+t28+n3Zvd0Y05fNG54KOtd6/426+dU8e3u1Ov3fk69fc2z4Lhiy/P+OHX8/2Xf026w431nnW98cz8bB+87Xf2d4K9zd7Os+7NxpuLwZnvef7F8aT7l/tima85F93jPc+0vrwa+s7g5OSvw6H7YmNzcjEYWIc3s/6byfMDf/ck2A++7rYPrL13fni3+uzwRXdgfj5enr3tb7UPnOM3q2Onvdx/b+4Nn+18OYDroj9rbdoHn9997Tsj57Bz/eKvKT8/e2meu6Htf9xaOxq9Wd9adY5WZwffOh+3brzh7v7Ho9Wjm+vN4dbJx1db41fvP7xaG64Fhy83Pz8/dJZXrwfvJvveFBHgD1vexuTu48h5efd1axRO2pOLF69ef3Ruzobe7NXmu42NPX584fZa6+++LJ+0T56/ed/d2tjYuuntrd28Xt+atP/a/3jgPDv6cnu9dTPe+9hfbh1PzjcOw+XPnY2148/7m/b7/fc7L05d56/hhf3q3fN3ux/uxh9fPrsbX3xcs5y19Vs+3jm627u97X4OzA/vD07etP/ibv/sbNCyX32bHd4MNvsnJ60Xu8vrm89eXnw5/OvZze65/WLr4O7D26+bz3e96dqLN18uNp3T0bkX3p58Dab95f2D1nv74sv1xsf3/Xf7/vBk/8PqZ+e8tclH3XD5WefzmbP5cu/DZ3e0unsxXT27O/zLXp2+XX13O7pttW42zj9v3hILNpuKQ2EUmCJ7kBQC8l6T43L/m+XJZCTsKDirKtTgLY4E/y79OJFklPKVlmUp3q8ioS0ziPYznXMUkYfHQj6rap6WxVlShP+iHKm52b0SPez9VN7Uj+byJi7bIJVbFT8mvLJy+F+RQacGT47F1GEVq7fz44jkOI/sVUp8d2bhN+7XVpExVIOq75MejzT4TGyxbkg8VAS1QFdSeP2IM+y3iXcyff8JoV4E9w920dk56HX2tynJqNY5FfYNUe10ZJI9Sm/lZR3hVOCgI+zIJHGehHzkE3gqkvPz034LDeZnp/1j4EVyWiF0/e7N/tl5+3gbV2Gweeygr5hVXuUQnMphvXp000Y6BGoJuSnlJLU3WMWdYCOAdILXTyB9fGvIg2q9lDfC9mEPOks/Ndvc5Yxoq/4qGfXrGZHB8Htg6ncz1o0szEf8f3N0dake/03qja5gK90954XUHU01cvNb0tHE3p2cyaUVHuro/pNwhM9LMPgJCxaZBcj8AlsllmfGrykzEOToMx9pwmTPbK+uxjbaNpllxlKcwX2nhz7neuDZk1zwT/e9L3K6UwQ053af/aDbPZoj5fw1+vjl+iHO1k554RX7yPaLvfG522MnZ539znHrSDjVuwetjecvthndIxMuIlpwEGOum75ljxEhDidT1bVKpJsordy7HgvT7jGzX2nj6NhcNCjA1fdmkUOqeGQYOUeU+pK9eYLgf03shRrRatq3pZNLJfxldB8aX75RkVV4pSkKn9WRPlqeUl5O4EQmPaWSQrIwLxGuY2sEPmg7Id2pVbDr9KvFg1wAlSHomUyaWEP6eeQul3dD9RZRauHlf1Y/La9qbct0wes7ksRtugGowJOLDVyQ7IC8yzuNMPk4RfQCwga+dmyza5mKmAxUN550zSIFvk6ERHpfdgtFjQovU+QvNvzw/Yp4utEAdUtl1ExJkE1m/bqlOZSuri3IsdIeZA5pdpKJa51dZiHAQGQR8kCDVS0V+TlLp63Ddk+0JXYRrNJgb1U3wMuBabB30tmVfqM8YAUZ/TFfZWdNwkZdUjPe19QMiIvJfWY0Y4QayVu5v/COdqj2XPk64AgRQtigV7lQmswdQmd1mj7kbvN2jnEu4pAk3WUbNDVVqCSbfW46kPBA3Ynu56JlRqhKLgxW6VVJXSyKZ5wWIAu8Yfp5pm4lXxHE2ClGv6TkrnhLf12BfYyOdpOZ/OkOE1qReh8dr9aQstSSrnX9AvQVhI9HwoAi10grSMRBHHu+qiuHL4Z8SGsRBFvLnVjIy1kqy+MC/JybhWA9AfkzaMWQ+2RUS6nwG/cRLxeBi2zAUzJMJjzHfUCNbyA+whJ9TleJQ7qxqAiI+SG0MF3AAqvlSmppqquqT8wb+iZIsfnD0/hDUCnmDzVKikXUs2iVkcJjyPv10bwiSarTPQ4Q9SBtEItifajTcJML9Tug3CBxOVr8OvPghUVUygyYR8q5O2JpYkQY5K/Tt19vK10BrBZLNQ0PuHdnKvUowknPdUoxX3xVQoYUpYLG1p+nAo1iIKVyup4nQzYyVKbg/2IA6TVZghPS0VgmihRFy4j1QjMQ5o282CKiSepG7pgLk+fR6FE2EVieV4V59TKzPGMwaTI7dR3tD8T4hBFGSqcW8KOFIMyJUlF8EBn/I3F9OG6Fw3lEYW+1tTT19p8M/N3PuRQkrqwUXGtLGT0pfFI0AuNQdgO10qYepx5LGoxEPvHEHIWa+qFzhjJziwKLKp91VU+o1zMOokGLeEEasTlN/P8NuciQ0xOnhFU3X1hsydtNjG5OGeKyo3go5U64QDhZIsy7tGDJWcqE3ML2VlAXr2mUt5bG81WCZ+qud7J0RM7m05c6AYWo51wYeBf8PVCrImzPOMybM+6i+i7brIBn4kC6svfmpf2k55Vlx+pCAbkAo7Z/K5aAK2efxCKz9R+DjRWah7aiYW77ZO4XY6AjiNnoyoC6ej4HVoF1FptcmIUUL991neo7Mcx3eMO+J8lOhZbYEc4iYqncreQIwUjWwjqhKxiFdXy2lSZGFF2Vsu4tt4eqRs5UCocjd9xgsPZrdD9qSEmoQ+Xgc+Yfd5rcTu6/JNQrUlUL112goJb6qjp/NDb/IrQhj2uxE2PhIGRAistXo8my25koUqSKIoXWN8q+arC+hWy5LCHGnEh14ltjOpe/iCQ0JyGPJuoLnKgSsSQdUzLxtsA0ETmlRSJH6tJM7FAyyZza6jtKecP8cKumdkYz2xZpZNIjhXs1cB6BAhbSDISvXHQFzgG3+1Em2x9sF5KZJOjIRciB1CLJHQeYczCB6SoK+myura/S/7iCIKccEkThhW+pdISRoB5FL6SmlFcnYx0sRsYT3vuoVJQwMCB7RL0lRGS/Jf5liRNdS8IFPhpDjAzHqmDhR3SxMnkLyQXXzFzhYIV+xK3VdEpX3F3sMFCgKm/cE6CAUim3mbwTkAxE3BeG1LY07/A5cq9NW5VDiAAxZP+NaEx0XHz+oJQTMkVc3EPAYUcGtLxRQhf9kT8i7qHCawAPmi8c0ZQNtyOlDJyEXF3jhBSKuhf4o34NYPNenYUP0T0G1H+bgH/jywkiR8QXGaiweaypsEVDbt8lqqmgZ4Bc5GZJ/ISVKtxCq9rVN+jvYMjcSseg8h4e2UMsLlhcLW5XmuYxi21HkNXSomXpUXVSwkjVEtOuu1VotMXLLCvFmMP508kmibBKQVbEslEbCc+UUc1PH+Bzc6ctL3tQgqyEQi4savuU+RfC+RkajF33KUQooEF+4gQzs6Ulxiri9U1bt22JQnZfPzp5WGVY9AKA5BKBwPVJfLMKYfCIEZGYg7+4MXOi40GG2mRNmj/vkTt2FYr6QoMJNJKGZ97ZLljwz3tcNZpS6aQLeBLosmhkCfybqXouPKm2dz3D0YSTlc9CWn0q6BV+qxuNqfkVlfHg7wtwn22rAU+6R4laM5831+obDRIRZEDEyWt6pp3MsKOkg4e8s3DnoAXH6Ru3D7li88QZhOk0C2ph4Yqd8gtRrhwOXvWCvD8omEdlcbLVcTIVxDbWxBVdmffAalplJpYrLtVgoCXuBoXNWTiqbWGl1aU+RJoYFbGKccWlntiRh1/rtBrWMH1XRjSDUV3Q3Bqm4z6iCYiDlayBNuSR1lPIdU2FCFh7cwKPj+zVEOat9KzKvS+zJCWqcl1gxKedbETMVdl/VTWJXGqyn+DiZtx9KVPLSL6PA16YrrwiSlaNDYuAKg4EM5TwguER/4xg6YoxRC1LukF6H40xF7ES+1EfHm2AK9OzKJ8SqZUB0jxjV54YJKUnzJnDUydQihZLKUSaoBCOVh16NXnAyRuj3K5liasoYJCEa2Q7+Qrco/8qc1PjVYmezrnroMBXE76SB12b0i+gi0buBVUiMrkwLClIeZ9phpYNgdOcHtgosGlFx4ef6hnVLXpi73S3VIr/4uJbCjAopPzflC3BBLWUqBQqN07BoG/6sTP3tarHSCVoZeW/aZTKQo4VZAodq170+pZuijjw7VrIebaDuIe2bemciQRoncSnyrG9FdBOBHGaaVrNW3O9C+al8ImWnKVgpGQMwFPiNNcklQ6rruTKFerRSnFQhrDF8YUOleKW0Xt5QVHUHo4j/9idc8aRL5X0ukHyCVVQKG4avU7TIhlWXJmMpiWxULhh+8aLKM0Z0UnYlduw9EibxClgxL0RLNGaNONBVhhXXhA0VsDRdh8G1lB0p8ngQcQQeBZhbcgitozyqeTGjBrVc9ZI6XVr57B9vMt67Z2D405354C9Rj5Wq41cK4pDRmg2YhjbCfUWmqu5o6V13Ls4OSOgcnfkcQEKyFViesYSRQqpt8TqeJe0q/gkWpg59Aez3Nc+jn1/lULHrY4oUSwMD9CQrt/QxVwWxQ2k0RxMZuGQLgfTCg9sbjrICs4HoU5en50cts8iRY8AL7Meaj7VdmS938ThHnsT/zmzrYwTisqWzat9+BsNObqgZhLPw4UwqgXWGG78ZK4uzDzdbEG1xcV2WynV2hosSLF/rF5B2gCQlQvyRoCWPyBHTAqzpkoaJAUNZLPE0ZRUvvWsovq0mVqwRVVgV8q7lLwrlivndHy8OATRdVkMVs11zVRbzb8vKpyaarCwxGqq5eJCqqmmhRVZc1f0r/MFV+9TZSfK14WFVj895DyjqSKilKqZpXOM2tyCqvmpSBWdDpisQdBxcGoo76ZY3MhGeKHZCHlYqgTsI5z9Oa7HOQ/5hVVdk7JnWrGN4qKuqSvhweKqrloidTZdOu+djSuwajIqFRctmh61zlUHKWr4Q/Vaf6ZWq06PuGLqD6UZLarjmabRgpIlBUsoK57Or2USFcPIv9PLlsiLaJozNZ1ubjzkR86XZ9W3WzEyuaY/ul6F+P/C+sU8/VN1V3Pg8k9UJijpAXHlVWFNpgqzxoVXSxkWiD07UbVVVWn1keKvAi5vRgcRM1ahCKzKe+2mXcMvBjxS7Z6RPusWZfQJiNDuMRNytlMAgfgjMkSFEZoYLFKVltWmHkFDCOE0HkixMeXVRkPCMBoRrExiQIyoel/nWoUrqf8LlBWe4osUpE2n8w1vkEv7i3hKINr+iFQvzXCUw9TJa4AS4Lk5/IjxKGBW1TLgx5Q5JU8Ojho5foHWIp6T2iKBaJiS9WcH+vRv1lflw4RNRPcczkhGkw3rdDumMBE1mxxZ0xPKakgoQyZaKiUEeQQE0lb5CTj5E3zmJGpEarcwbKKEDQlFXNCVMSFJssddyhSVIIXfpOiD/GQHk9/HGLiUPanqSwCkGGgFKA7sGckZUXYJWstU1OUXd3KHWrklCZw0TtGQe/B9U7xYmAlUVp6kxWxMgQRAiy7IDmTpiJpN7gJTleQL6MYsZUkGWkyEvity+qtfIPmR0iLxQPk8k2MxAFVB8K9F0Q1S/3NcKobcoeSyMViVdgTl7isNlvjPqDbUPmlGDFvgbs0pUBLwWfKJkmb+uz/kCFxPPlzxjGWS79O6iYYpEIjve+HDKToV5PdXZhRvoL+ST6jEH9JY+ImWHNrUPLqELnLwxjXBEyncYuGXvlUmY/1qIWT0XoX1ozUhTwHP3SRbymoe9xnluYiQxQkF0UBy16QHajBqhzIulBfGZMYdpRmIZCOP6v9d4xswdVXtMapcLjPwKFvLDotTDlDZLnP+irN3qeAwTfOfPOQeCpOuhd+hy46RVfoO//ZOTo5qO8gy7RzvP8nvsEhobaf8AzWRsyYyPGW9iuvETUgll1GxIuTCkRdQfbdJMTEKo0MJFrkvUKVus6hT5j7lPVi0SaiTfi6i69AK/oHDX0Z+HvKcmlq0i9bZ8fkxLgQK8SVkK4olhDwuhhKrASq/QDjPddUyrno/L3mgkZRKgdYW6SUaE/3uSJzKIVlK70191hnfWCJ59toHR8RlPz7Hs8jdWjDHpSxDzWEmmdSaqm6Ylys6/mcncAC2KVebslJJakG2fgOSfXM2Ta+g/pGo6FbVTyxlNM25U02U6qRSHznoRdyGcpJXqNAQ/bW1oqr53Os7KckAlP2SvOb7gkQgreGtJerTiEq4XH5gbJ5oSVhO2G45impQ9YTpYnI0isiQKcpXmLBbzaYzp+TDnNRmVR+84Kr0/1XyscoNk+nAIle0LbOghWlD5IrzHTOmb0Fof1HC8V5c01hnXZVyHT6ukhYfybnFjsfTPpyWOX5/doMs3CQJg0RqVQF9ZLxLqDTiI1JF5Pk20/LQjYUs/+v3f5Nvvf3WK8DqQ2+//Qpw6ntvv/vut3ZzPfleyz94fz35Zss/d4s9/mzLb61FoGocaB9t+SdKHWgfbslXPEiljc1EJq64jeCL9MkudjqcuIjDxOmTJNko/tvTLnoomzQ+2ZBm7pOUtbk8337m2sHK4k6RSUNmXd3j0x/vMCCfjeiRPWPnmajadBYnc0tFZX4BDR1QURENaDiNorxegdg+rBtrOhSp8xHdSQLTrWACLz9RQcDp7NIXoVqdd+JnrJwiDVgcBvrYyk2nYfCEM+BRZVfXEOZ/saeoblVUM1d+njc1ClmXnCr90ydq/hdKPHCOO3kAAA=='
}

[Environment]::SetEnvironmentVariable('MEDIAHUB_NULLTEST_SETUP_HELPER',(Join-Path $internal 'web_test_setup.py'),'Process')
Write-Host "`n===== TESTSTART =====" -ForegroundColor Cyan
Write-Host 'GLiNER/SmolVLM2 verwenden die bisherigen echten CPU-/GPU-Testablaufe.'
Write-Host 'Speech-to-Text: echter CPU-/CUDA-API-Auftrag mit /plugins/plan, /jobs und /execute.'
Write-Host 'Interaktions-KI: echte Node-Installation und Chat-API-Auftrag mit CPU/CUDA-Backend.'
$results=@()
$processedKeys=@{}
foreach ($item in $queue) {
    $itemKey = $item.id + '/' + $item.mode
    $processedKeys[$itemKey] = $true
    if (-not (Confirm "$($item.id) $($item.mode) jetzt INSTALLIEREN und real TESTEN?")) {
        $results+= "$($item.id) $($item.mode): VORBEREITET - NICHT GESTARTET"
        continue
    }
    try {
        $media=$null
        if ($item.id -ne 'interaktions_ki') {
            $mediaRoot=Join-Path $item.pluginRoot 'Testmedien'
            $media=Get-TestMedia $item.id $item.stagedPkg $mediaRoot
        }
        if ($item.id -eq 'gliner') {
            $glinerBackend=if ($item.mode -eq 'gpu') {'cuda'} else {'cpu'}
            Invoke-IsolatedPluginTest "gliner" "GLiNER $glinerBackend" (Join-Path $internal 'GLiNER_CPU_CUDA.ps1') @('-Root',$item.pluginRoot,'-Mode',$glinerBackend,'-GlinerPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
        } elseif ($item.id -eq 'smolvlm2') {
            Invoke-IsolatedPluginTest "smolvlm2" "SmolVLM2 $($item.mode)" (Join-Path $internal 'SmolVLM2_CPU_GPU.ps1') @('-Root',$item.pluginRoot,'-Mode',$item.mode,'-SmolPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython,'-VideoPath',$media.video)
        } elseif ($item.id -eq 'interaktions_ki') {
            $interactionArgs=@('-Mode',$item.mode,'-TestFolder',$item.folder,'-ExePath',$item.stagedExe,'-PluginPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
            if ($DiagnosePause) { $interactionArgs += '-DiagnosePause' }
            Invoke-IsolatedPluginTest 'interaktions_ki' "Interaktions-KI $($item.mode)" (Join-Path $internal 'Interaktions_KI_CPU_CUDA.ps1') $interactionArgs
        } else {
            Invoke-IsolatedPluginTest "speech_to_text" "Speech $($item.mode)" (Join-Path $internal 'Speech_CPU_CUDA.ps1') @('-Mode',$item.mode,'-AudioPath',$media.audio,'-TestRoot',$item.pluginRoot,'-ExePath',$item.stagedExe,'-SpeechPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython,'-AlreadyConfirmed')
        }
        $results+= "$($item.id) $($item.mode): PASS - Installation und echte Inferenz/API"
    } catch {
        Write-Host "FEHLER: $($_.Exception.ToString())" -ForegroundColor Red
        $results+= "$($item.id) $($item.mode): FEHLER - $_"
        if ($DiagnosePause) { break }
        if (-not (Confirm 'Trotz Fehler mit naechster Variante fortfahren?')) { break }
    }
}
foreach ($item in $queue) {
    $key = $item.id + '/' + $item.mode
    if (-not $processedKeys.ContainsKey($key)) { $results += "$($item.id) $($item.mode): NICHT AUSGEFUEHRT - vorheriger Abbruch" }
}
Write-Host "`n===== GESAMTUEBERSICHT =====" -ForegroundColor Cyan
$results | ForEach-Object { Write-Host $_ }
$summary=Join-Path $testRoot ('Nulltest_Gesamtuebersicht_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '.txt')
Write-Utf8 $summary (($results -join [Environment]::NewLine) + [Environment]::NewLine)
Write-Host "Gesamtuebersicht gespeichert: $summary"
Write-Host "Testverzeichnis: $testRoot"
Write-Host "Version: $ProgrammVersion (Interaktions-KI LAN-Autostart; vorhandene Firewallregel bleibt unangetastet)"
Write-Host 'Keine bestehenden Testvarianten wurden geloescht oder ueberschrieben.'

if (@($results | Where-Object { $_ -match ': (FEHLER|VORBEREITET|NICHT AUSGEFUEHRT)' }).Count -gt 0) {
    Write-Host 'GESAMTTEST NICHT VOLLSTAENDIG BESTANDEN: Details siehe Gesamtuebersicht.' -ForegroundColor Yellow
    exit 1
}
