# MediaHub - einheitlicher Nullinstallationstest. Windows PowerShell 5.1.
# v1.0.20: Node-EXE-Auswahl aus v1.0.17 wiederhergestellt.
# HTTPS-/CPU-/CUDA-Tests aus erfolgreich getesteter v1.0.19 unveraendert.
# Nur Testordner werden neu angelegt. Kein Git, kein Release, keine .bak.
param(
    [string]$VideoPath = '',
    [string]$TestRoot = '',
    [ValidateSet('all','cpu','gpu')][string]$Mode = 'all'
)
cls
$ProgrammVersion = '1.0.20-interaktions-ki-tls-node-auswahl' # Sechs CPU/GPU-Nulltests am 31.10.2026 bestanden.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$base = 'D:\eigenes program'
$pluginRepo = Join-Path $base 'MediaHub-Plugins'
$nodeRepo = Join-Path $base 'MediaHub-AI-Node'
$sourceDir = Join-Path $pluginRepo 'release'
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

function Confirm([string]$Message) { return ((Read-Host "$Message (ja/JA = weiter)") -match '^(?i:ja)$') }
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
    if ($matches.Count -eq 0) {
        if (-not (Build-MissingPlugin $Job)) { throw "Paket fehlt; Build nicht freigegeben: $($Job.label)" }
        $matches = @(Find-Package $sourceDir $Job.pattern)
    }
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
    $chosen = Select-One @($candidates | ForEach-Object { Get-Item -LiteralPath $_ }) 'Compute-Node-EXE'
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
    if ($childExit -ne 0) { throw "$Label FEHLGESCHLAGEN (ExitCode $childExit). Protokoll: $runLog" }

    # ExitCode 0 allein beweist keinen erfolgreichen Modell- und Inferenztest.
    # Nur die eindeutige Erfolgsmeldung des jeweiligen Originaltests gilt.
    $logText = [IO.File]::ReadAllText($runLog)
    if ($Label -like 'Interaktions-KI *') {
        $expectedMode = if ($Label -match 'gpu$') { 'cuda' } else { 'cpu' }
        if (-not $logText.Contains("ECHTER INTERAKTIONS-KI-CHAT BESTANDEN: $expectedMode")) { throw "${Label}: Chat oder Backend nicht nachgewiesen. Protokoll: $runLog" }
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
Write-Host "Tests:   $testRoot"
Write-Host 'Fehlende Pakete/EXE koennen nach JA-Abfrage mit den Original-Buildwerkzeugen gebaut werden. Kein Git/Release.'
if (Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8766 ist belegt. Fremde Node wird nicht beendet.' }
if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) {
    Write-Host "Release-Ordner noch nicht vorhanden: $sourceDir" -ForegroundColor Yellow
    if (-not (Test-Path -LiteralPath $pluginRepo -PathType Container)) { throw "Plugin-Repository fehlt: $pluginRepo" }
}
$selected=@{}
foreach ($job in $jobs) {
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
Write-Embedded (Join-Path $internal 'GLiNER_CPU_CUDA.ps1') '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'
Write-Embedded (Join-Path $internal 'SmolVLM2_CPU_GPU.ps1') 'H4sIAGYH5WoC/81b63LiyJL+76eoYIgRikbypecWEJxobLDNNAbWYPfssXtZIRWgsZA0Ugkb+xCx77BvuE+ymVWlK8J2986P9cS0LVVVZlZW1peXKv1ArqhlG5fRjIxXnnPbvzoh//Nf/03s0HMMRi3yTANPs92QGY5DzkY3hxejG2K7jC4Cg9meSxgN2cEP5IvtWt5jSEbeIw3GSwq9f9aPdXIdueTRZssG8bElxBadPlGiDbxR4M1tB/7sPlEzQmojz7HNDTnd+EYYEu0cWyu6rvvhceXANwJjVbsLWWC7i6/VW9ui3shgS9IiilJP3l97HsNXncY9tRfUpSHxAw/EXd2bS8psEtrwO4jcRUgsmKPt3p9khl95FsXhph9l3qJyRob5YCxogd1ow5YgeKZNPTCd8KDaDQIvaJt8WgGd04C6Ju8wZp6vHFRHKBQNw0IjTNllzubMc5ntRhQ6BmJCfGIHVdDd2IsC3vt3z3Y1rgLRSfm3CNRL3ft4UbUzb+VHjIKyLYpqR3LUoUb4vuEjJ1rA4t/LMTA6REU8LGC0PSe1rF5U8kJyetoS6gCflxwfyVyJWUxjs7u1Q9DUdH0EVvNRXy0N2+fMFbI9qPpCySnfnNY55/w6vI+3GAMmyuwV3cM6NAPbZ40xDDZhQ9yCDaPZt0jtLqAL+vS10bgymLms3fWGOjKCFxeUoekOjBWtxRpT68p0Xbv7j+nXD+p9hklVUVX9IvAiP7w7/qrfGk5EYZEiV9pxcZFqChJcO6uTqUI+EGGvHwgQ54/l4qoHVcdblFKL9T/9DKbiUMamg8hxcFdz+jWYi9aBbQK70QtWBljJBn6urixrenm5WoWhoiJ7nT0xsHxQchg5LARWn2rwyALDFSKhBc8NWBQwYXc9NtYALtDpZXsw9wJqmEtYVRcUBuACQ5XRv08uh4NRe3Kp1OXD5fCqmzzcjLvXp+1x+mIwxFfj3gRf3fauJzft/rQ7uIWns+Gg056OrrvnvT/g8arb6bUvb06n46thn0+9NxhP2v0+dBme9/rdbJ+Lfm/QvX6tx9nwanQz6U6vbwaT3lVpU6c9aU+vh8MJrDV5OSDwkyjhjs/6K+jiruuu7cBzVwAAwogyL26NwDZmDhVKgkkHnklR+QepjRq+3Y44HnK1Ri4HH9L2bcm0gKA3gZ3BPQp7wWopwBbQzZv9CfbztXrqWZtW1QWLqN8tjXDJUIav1UtqWGBZLeCTUkCTbyH88fmZ3mpmu/EiN0m6yg90g4tckFr/TDch38nxyDvsiYop9JTvS2lKwV4jJrvEVIS0PhcTFNJCrTSlMqRSmvF0E2rNCQCGF7ExNVu/nhwdNTNg3xIALwhzsELFcGF8vedyLfFXTXyBOA/LO9n4oDvD98H/cb966MH2ZRrolhorhWSo4WIQzaWEL46ky9epxt+QfxEguqYBm3ja7yEYgNahPpjFxyPC/QE6HbX5Gu8/YVSTmEsjCClrRWyu/RaLEFAWBS7puWvvgWrXABNCR+STf5CxOeTbB8R5KdrcxGYOTe2Lw52wmC+BDY7q0gsZqWiaRkRXAn9Wiu01MW7vTH86UrPC8JE3bP7brjgIhakFZ6RBNMdFgo3Ih7cdZ0KfWE2MED3rtQF91IZ8KgRb9ZvJ+W9d1/QsIFcTcKeqOVnQNtAZJ6JU5U5Wy1Y4bpP7F39YsMk8xWM0F8A87q5fGmH3CYS21ELXop5RGp8SIwpDc+nYMBZsYAlzCRkPGcio1yHVREa9Z6mVHYI/EmaEDw+2DOwO+Zh0BDmckMNzcvKPH49hwcCJdGHLxlp7yYpTnUoji3/Spy0x0cnm+1dQRI3PQftiBC6EdA0gUpHjtqD3VFtjZgRMm6T+SOsDocBwhDdE94gezkSrGkYwfVgEgQ15H8YC8M9FPV50x+2rCTiHyfDzsN9vcHpCUylGzYVrSyO4ehwb1NMAR80uWbKyNb4iXNK82HPC3+IWJn1qzHE4YcvAeySV0RwXk/EYl8zp0mEg17yS0Wp2CiPjgbLD7h9d7ETGl+2Tn39pVWvc/+NGAJsqYd52Fh4QWa7kCBVtbymNJAWtvfLLOEclmuEChnBuZ0vbsXqMrsr7ymVSAb4gcCPagpGjzKyR02MUPFOHALYtDeowMoP42oagBOMYt5FQilWBu1jww3+5Ljt2AObpgfVoZcyLNvIDuYBEI8AwySAWBaFXtmuHzDZJuAEpKP6FMRVZY9bCMyJyfr7y6YKESxv2oAXGEUJbmob5IpTVJYPJ0uaJzBryGcNkkeFIWhYVeHNouzKPqBO0GWiEuHYuMZ14cxDtwfUeXTK5JdSHDM+SxFMASXKqrBW2LUvjStHaYUhXM2eDgS0Zb0LQlg44GTsVYPNdgzjQipZkfHU+hzUoRKxyDRTUJCSTD880WijJkPcso6BavoiSbZ6nGKDM57hWIoNK+j7bGDbcFSbzT9uXjmPoU/caQoc0B3gFxSEgxJctTlbvwgPAMYj4BXJVmsJldaqfg8BcmRr9iygrTGaW0UyP04JD5nlOeCgkPswIDiD6LyISg5ge7OwAjPJ4x59IHwQMhFzpBlOk2XJAIfYqMViNI4hOTm2G2UKanhvugs6oqysFdN+juO4TbFJ8EYIK4SEAa5942FITstRhUerSuWYcxNx2DcfZoI5Qgx079L2Q1tQM11zNoMywZvSRLsC6pmhhfHvpK/+ndMl/5AaiLaFlOjNc2PJEA6R36BrhBmNAooGtzYljrOc20Wxhq2FgnrRC+5m2Pp4cPZ38dNRAqGidNKxIVFFaPylEMxtrgqr9iWh/wZ8/Z8TNeYRqvz2edP/oTc6GnS6PEzL4p0xiybVugPsDnCJfqwVFFw+Aki7E9uB9TibV2n5nk7BNPE0yKobZrLeZdMeT216nO8x23Od1sgK86nBSX7vC4EW4W0yQc161OvccCOfLTYCPTLsGojZQwAQxXpGNGUTwvQCDhN9+/eWXzEsIhXBfuzmggewBsgmkfOcFQI5aXz+9IPMWF6Epa24t5bzd6ytNfJc8JEgfvwCXY9jQrDSFbC0p4/YVwMkux3+6reQH4z3kpk+8G3BMQQ2UN7jp92UK3J70hgOSdq9wNKWLALyxdeY5sAXONoabY/UuZBZK3Q/NAiSf9qzFKxWvLIEzz99oJbFFWlWDFAL8tiucJr7PCwDe1NgtpUgrUURJZypd91R2Vr5ZGTGX17XxAxm6AHh+NHNs2CYWBX8DTt/cEOYRxzMhRJCSEEmwSTpDMhhOSFzRtZleIDlZUsJD/1UElmHZoQkhR1AnvmO4BIO0dCiZQdLNQurMyeOSumnoApFKGM1W6Ags/V36Twt8ef1LufcZriIqeESW8AikMBAODm6uCXgHwh0SuijHezAcELCTaEj7LDVcczFGjidlQy6p6spedh0wNa4cywjmJKQ2gO/aCwBbKSgAOFzYDI3wEEHHcbQOhFuOZ1igD+rMUJ9gY8t5RJcB4nDetCDXhokveO3sBcCarozpWtTvWsdNFyhOsfbTqiQeN67UaXzDVppgBuA7p0uQtaUcn/yqH8F/x0r8HtGpxTGqSeOKe+vTi0XnRuSwKQcfxYiYpzRNP5oCskPwEsavFvDKomvbjDttm6YHLtCUZAL6VwR2PIW2JUaeIu5s8YSpCbr1HqcBXXmMTv/0ZmFLOPDtdlfXPFOvlW2vWEM6FigUFXA+0dm+UsDxkZrj8H8tNr6vsrinasgdZqHMN36tzCcqb2mxrxhBvYtUWYH0WMmWEL+D5v7yZ7xcfzeDtIj6t7PYXwiu1njExcMJHm7DLoBleFHMyDKU+JSBHxZt1X3iIAkMaAaUTc5GZ8mmAQxEkB5h0CBCB23MMIfs8/1KtExVkRQPhrKJfkpgBuH9gjXJA4emOWw4gDsCYj2DWBSaOf7plYIhxTGKKJLIWYjzt8Q/Eu2LFzzAZku9VeK0R0YYTpZBlCcaBTbQrCwZ8xuHhwkeNbio+TpSFaFmk54RFLYsLIHdOmqSKsTUkHUcn/C/P3woq2+JOYwdSn3QJyTHLsDv8U43vq447Vy1LFYpB3mhLVYn2Gzim6ocgi/OMK4sKjIJtUh1SQ2HJxpYf6+gMg7Fq0pTMBdPOjgeFoXCurwHhRd0uTYkdJIZPD1AgpPUwPYVyfK5PKdRmJJ2KYTKJwQNvlTFqcQlXOWy2+4DMsYzyq8b8x6oW5pRxZBtAm22uTd8e8o7C/AuF3pvCpKwyeQcSnvU0ybYIHKOYn5ZBZaiGWJsWeIVmYUsfO/jQbRr4zH1KOeBt+I+RdWTSexu8ISb3qfuAomAoX48KRUXcrKIOsxe7IhccpJD8C/IeZ5FSNQiyik1Aox58bwvmWOB0CPsVYgdTik6vJwRypbK3mTgC++AcQ3pibCIcwYrqUE6lSOsyydZjCsUh6t4YoQnpa/UEOPz5D2JHSQhfbw30HPXCNsuq6kFFuJohmtK+UMeWHNm6ECV1lunss10kOCrtLjYRXzE6DerRRHph4fYUIE4FDSniBQvlSlmUr6tsvnUeNRvDxTBpmAQjPriNJU36vwfO7MsU96joBXbkmPE8JKye3Wqy2TFtshW3WsM7dnSAHu2Fw9YQQ2oDbEdoP6CojlwPtqfsO3BGLV/EKVgACkYJbIDu8yW+AxuisjXhAZLwJeSQhGSSetcIlWYxsk3QQZ49MdlAZvdrYjl+mS4c5BfGixOH7TcZMmgd3Y5IRjqrkDTAJYEpF1QFJeVynhnBIGxAUvrgdt4Gs65fup7JVeJBpnZW4OSSWSR7xycJCQIJL862nW6PDsCVuO8bZ8VH1Zr+WU6BNc5t4NVwbyz++yVLVNu593ri+7poDdWEnn2GIxsjU0965zFuq0ohB4sh1BE5HI0QA2AqZrLXS3IsoueakMZtcdjpRQ923PG60RvgCff5xI1+a7LDo8hsrSUK9rQ+MtrubKDIo5HYACgGoSuojsPD5IW4Zw3JS0i18NxmcZtiQdLpxGfrUAMeZxRfJJ4yskKfYvTlaKms2lzcVxAFzY6ZHCudWI8MHst/oSQJAKZ8X8jCnmaPDMCWMSdEtNFALFZoXIhcu4sNhLggpuWdHsXXUjIyNhcglisQSybEmnDOQtCU4P+jkEtGBmKGeoFXyBqDq9WgORzeB+v5P2auuv7MXfv4b0gsVueqq4MFyKy4FXi4f2Ondzz8uBUjgagKZLF5vBbRRajlD35s8z3LU5NlFrFtOrxLNSy8PztWC9HeH/FWZZYbr0Aj68pe44r3Vh8ztKokNcCZqGbnbMmqbHUdH8+OroShxrcYoLIZEJBSjGREZwx1BBOWDEsi1oibpSli7pigt+ZMrry8Zpl8hIBdxE/LcSRIvr4fANnq4fGnOJJiReE8M4PqC/SNi8odN/3PvSpaRuOFAyMx49b+Bv7GSyp+CJHohB0rOwwBAcpIDCvhh3se9UCasV1wNWpTtWiMZSCmJSicDr86i2IEuAQKb/Kg5wcRZUfItsy58BUeoc0bIMzcYn0k3Jgr3heLn459kyPmO3UCeqvTnyYDryrk3ATHshNM/VFMiXbePBag3bdCBbru+OvapMI25zKe6HlHU++qge4wHhhMsdbx7fTOeQ0U7x8O8U6MU45jbCmyQXDHKooICYLalkxVfUAukQO3eUi3gs+yLGG/4Ds+EvHkigYFzqmqehYE79AZpENt4h4EftpIUotM3P1wIeMjtVQk7oVrfywJsbWCVhzhIXI0LTtFoZKtA4AhcfhrRMQGcwErU/01heU1RSeKyuw3Kg/Csl97UQ9UD6VLe04vglScgjBxXOmufAc67M7gJyvdaZUpemUXLGJvU6mb+wrYqz6nhs27zpTLNsg+QoCqaUlkiwl9S3s/X8MGfnJQ1Cy9hwHNEBdy15kgSHOgOqY/5SkBTz93T3zKBW5BNtVNa0o5I96hWQL+sjDMIfSYH+8y+mWR7s5KIRF6/fJ7bDfh6i9O+j0LhqpeJX3BGLVP71ZLmbGcn+SQ3x6gccp41cO+XkxQAQk5FOwZWcT2qHS9I0N4kPr04vno6nhLVPRx8T1aX1sgkNb+ayldCiWS2aUeHgM9oiZnB0S06FGAM9rO7Qx5oWlYXh3Rp5OIyWddDyOAYsI65wMLxoCbvjU82EAzEpejyFutJrhdVJlu80dmcwMExyi1fqm8vB2T4L0+/CUtAcX3X73YqJw9e3os2dlalj4Qkct2tae5ImP4IXE0rGY8b81UprY795M63VEWLVrXJGPK7Wz2IeCzKHt+hEryx572PCOIk16HWlbdhkip0V+m0C7GfWH7Y4Si7ZzeAwrSPcLLDvEIpcz6p5dTrpEsOsNzrvX3cE/lZR4sXwj3VmyAHE/WffNd8dgMGQ7lwXSDE3WikU5A0JLU1zapxbGc5FpUmqlf4cYGFqeS5XSSDzlVqqN3cAmZ7EAD5MbzOMFlV3qu1MXPcsm/rdMMAZsEaSD5e7WAxqxWG/4JX6X6HeOY+ULW7inKzUpMu7ia118E8H3Y5awHLR97fJV3F/S4AWu/c06oD3srPz+JcZMOGoPsiQIOg1ANH4+JBNmbcgHYb13afDToTIngj1a+xjuVsLiJRftyRkHKCU+48hncVKGsgWr5YmomTeQrYb4/c/OcRZHeVkClX2lwKKlJAgQDZnCx8eMlN3g0QgYhczyI+HmJXo3k5ollzNLYkemzD3gQJ48ywFqPkarVc55h5ejLZlRm7wcNwbH27BBXk62FbxbJobpGNE+1eUDz9yZsfLjF7E/1Rl9Yuq3yFK6MeMFbTR6Id46GAZfliDx2DdMmq52GeuMFsW8YkWJCai8AMuPK13Q5oPh4tGMuE1fdrhWFXdfT4UDzqJLgbl00eUwkzpsdM1y3+Ypc1s1hTuPJ3A2utEwAMV7JnNprEY0x+8iG4XxlX2Bdj5WeIU1RhAZ3hf7eN902m8x31uZq2ScWff6c3cwuBlc7NoyORf7CfklbXdHX3e0rb4vQkyLsJkvH3lgSvZK+voFtdzltA9EhrEfSJmzJqdd6DzodN+4xpYXPDl9LZ+KuIGHEDnVu08m5aErSDjm1llTv3Ne593Lfvf6dTmvC74pm+/lxSu7LXuQPzuXX6fwY+43jyYLqItXlPp778Y53iK8N+XtPOyq71yNww2yryooib9Vy3njHiPYhdYfXmQVukNu/wlxPEEt/saH4Ac/3/9ViywYii8mPwCW+aEZhcxbxZ9HyeV7xx2puATBP9yUvi65JRXfNd13Seq3zD3qzM3gvTdExecu8VnOOy+DJhPl6loZTJuIMwkwJ29sP8fXHMWOwfw/YZ/cU+ZVgpjK7nFKfKjDAVTgCQ+YpjL93X2fIlCmbavuqx5mDzXi6TfkQWGKKvgBfdd2n6mzpDZ6M09cfy/buU1SXTjezHAauQpMS95YSb5jLucMjofcDDoEP8r/Pgjce7iCn0/lIG/3e6f26en1zdkl9xflqKdWvnXSRWTava+XfDmbfOT5TTfqCt/d7l6u4146/eYLGSAsZj8dS+/jluyUCxoaKwb4ybwHz3Hib8G2BwecctnEMRzg52xYeiTHQPR/AUSl/3OYQQAA'
Write-Embedded (Join-Path $internal 'gliner_echter_modelltest.py') 'H4sIAGYH5WoC/41VbW/bNhD+rl/B+Qtl1NLSLB2wAP6QNt46NHGM1AU2FIXASCeLC01pJOXYKPrfd0eKjrPaw4wgko53x+eeexuNRve9tqzVasd6XYFhrgFWG7ANSqS2TigFFeuM3AgHbLFzTavZk3QNy37PR6NRItddaxwTZtUJYyF+/2VbHd9bm9SmXbNOuEbJBzaIF/gZVax0e1O7s0nSseneZ35lVv0atFvQl0nHSZeLqirEIE55lpleO7kGPmEG/u6lgWq6ND0cU+1MW0tFqmXTyhLsNOVl1+M3L/tK8PF3PgSC6XKPhTxZRGDa1qGUYkhFPtw+zpG5Vm0AFWDbQemQuynzuj8yPrBYdJ5FTqIyvGc/5a/P89dn2fbni0xYZ4TKzs/O35xdnP3i9YJaDlvgiShdL1S8HNkicdk78aBeIJA1G1R/mLII5/n8MmH4M0JaYPcB/8yY1qQ1n/2xnN3PZ/ds8efy/d38kn0Njr6Rp6/R1TeONLjD+FS/kroYyLAe+EpJDYYnnSgfxQosqQflQcCTDehNQQWwPyOJt76RD/5Jp9mzRd0aVmF5sjTKJmzvZQgMo69yaYtKmhgr/UiDKoKedIRcp9V4HGsvwI1frjVlk2DaqHBeZu8SyyWQMmG16m0Tyy0oBz/Fuq16BaQbBHlRUOkVxVEjf92Bjf/+PyYbMFYGTNFmEJ0wozovxEZIRUXzbEdyIm1/lI5f2uM4aJ98UX8m5iL9z1U1zknBkB0p7LNyROOLz2MI1yczcDRgGXJGMwNvI1++3IP6npTxEb8x/RqrUuhdSi5ynGTGWRpc6Za9wpGUW+jGjBBs6fIhsINKOdIZsTE+ssXVh9nyknF0Re5Ds+XDZGHT6TBK8P7K4zhJ78ku5O8+XV+xp95UgLVtlNArN2HSYkwPOKe1LBtHB3UPqwdh+DEIONQ8Av7KvxIQDPW7EonEed1wOpx5xHipN523Gv4D7uJTtgSE1wjHCHu22C3JV1wjEoxDlH4ThEzHRfDbjcRhk2BqQVG/7ueAlxzOkWLdKyezDc5KHvRRN5jn5LjoDODwRNXKd/beJZajakuhfNnYghbeUNHRi3/mrk2HzJ1IKOKBwOw4sbhQQJc0t/iVXoES7BbMI7rbSD9f2FtMHDKOf3elaylvONUvcp6gpXTSj8NwMQKvZOmKeJBG5xP2mXeYDVwYuKAoCCfDe4XTiH/BdmloX7eqmp7l52/2PT7DAoGBnGyGsLTu9Yp6nXZzXvXrzqbxugkDbXuD682WUk5/FRjmhFVQCyR8ilT+aw4M7YVhUnIR5oEnhUU6ZthYpBHFpwsnIEQrqLFCgD0Cpo8hj0ITA2xGHgTgKz/VZvuJr2Hr0oFQYcQarYyl0VDBBjd97nYd0A47NDuF65bcKKYE9LUb+k30ta9t/szyu/c4Etjt3fXs5mY5+7hkb/Hf1fx6NvcrIoJ9Sd8/fG7pt3kJAAA='

Write-Embedded (Join-Path $internal 'Speech_CPU_CUDA.ps1') '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'

if ($selected.ContainsKey('interaktions_ki')) {
    Write-Embedded (Join-Path $internal 'Interaktions_KI_CPU_CUDA.ps1') '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'
}

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
            Invoke-IsolatedPluginTest 'interaktions_ki' "Interaktions-KI $($item.mode)" (Join-Path $internal 'Interaktions_KI_CPU_CUDA.ps1') @('-Mode',$item.mode,'-TestFolder',$item.folder,'-ExePath',$item.stagedExe,'-PluginPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
        } else {
            Invoke-IsolatedPluginTest "speech_to_text" "Speech $($item.mode)" (Join-Path $internal 'Speech_CPU_CUDA.ps1') @('-Mode',$item.mode,'-AudioPath',$media.audio,'-TestRoot',$item.pluginRoot,'-ExePath',$item.stagedExe,'-SpeechPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
        }
        $results+= "$($item.id) $($item.mode): PASS - Installation und echte Inferenz/API"
    } catch {
        Write-Host "FEHLER: $($_.Exception.ToString())" -ForegroundColor Red
        $results+= "$($item.id) $($item.mode): FEHLER - $_"
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
