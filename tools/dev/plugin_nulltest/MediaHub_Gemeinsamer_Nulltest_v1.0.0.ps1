# MediaHub - einheitlicher Nullinstallationstest. Windows PowerShell 5.1.
# Nur Testordner werden neu angelegt. Kein Git, kein Release, keine .bak.
param(
    [string]$VideoPath = '',
    [string]$TestRoot = '',
    [ValidateSet('all','cpu','gpu')][string]$Mode = 'all'
)
cls
$ProgrammVersion = '1.0.0' # Sechs CPU/GPU-Nulltests am 31.10.2026 bestanden.
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
    @{ id='speech_to_text'; pattern='^MediaHub_Speech-to-Text_v(.+)\.mhaiplugin$'; label='Speech-to-Text' }
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
function Run-Test([string]$Label,[string]$Script,[string[]]$Arguments) {
    Write-Host "`n========== $Label ==========" -ForegroundColor Cyan
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $safeLabel=$Label -replace '[^A-Za-z0-9_-]','_'
    $runLog=Join-Path $testRoot ("Startprotokoll_${safeLabel}_${stamp}.txt")
    Write-Host "Startprotokoll: $runLog"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script @Arguments 2>&1 | Tee-Object -FilePath $runLog
    $childExit=$LASTEXITCODE
    if ($childExit -ne 0) { throw "$Label FEHLGESCHLAGEN (ExitCode $childExit). Protokoll: $runLog" }

    # ExitCode 0 allein beweist keinen erfolgreichen Modell- und Inferenztest.
    # Nur die eindeutige Erfolgsmeldung des jeweiligen Originaltests gilt.
    $logText = [IO.File]::ReadAllText($runLog)
    if ($Label -like 'SmolVLM2 *') {
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
foreach ($id in @('gliner','smolvlm2','speech_to_text')) {
    if (-not $selected.ContainsKey($id)) { continue }
    foreach ($variantMode in $(if ($Mode -eq 'all') { @('cpu','gpu') } else { @($Mode) })) {
        $file=[IO.Path]::GetFileName($selected[$id])
        $version=([regex]::Match($file,'_v([^_]+)\.mhaiplugin$')).Groups[1].Value
        if (-not $version) { throw "Paketversion unlesbar: $file" }
        $pluginRoot = Join-Path $testRoot ("${id}_v${version}")
        $folder = if ($id -eq 'smolvlm2') { Join-Path (Join-Path $pluginRoot ("smolvlm2_${variantMode}_v${version}")) $variantMode }
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
    if ($item.id -eq 'smolvlm2') {
        Copy-Safely $item.stagedExe (Join-Path $item.pluginRoot 'Quellen\MediaHub-Compute-Node.exe')
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
Write-Embedded (Join-Path $internal 'SmolVLM2_CPU_GPU.ps1') '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'
Write-Embedded (Join-Path $internal 'gliner_echter_modelltest.py') 'H4sIAGYH5WoC/41VbW/bNhD+rl/B+Qtl1NLSLB2wAP6QNt46NHGM1AU2FIXASCeLC01pJOXYKPrfd0eKjrPaw4wgko53x+eeexuNRve9tqzVasd6XYFhrgFWG7ANSqS2TigFFeuM3AgHbLFzTavZk3QNy37PR6NRItddaxwTZtUJYyF+/2VbHd9bm9SmXbNOuEbJBzaIF/gZVax0e1O7s0nSseneZ35lVv0atFvQl0nHSZeLqirEIE55lpleO7kGPmEG/u6lgWq6ND0cU+1MW0tFqmXTyhLsNOVl1+M3L/tK8PF3PgSC6XKPhTxZRGDa1qGUYkhFPtw+zpG5Vm0AFWDbQemQuynzuj8yPrBYdJ5FTqIyvGc/5a/P89dn2fbni0xYZ4TKzs/O35xdnP3i9YJaDlvgiShdL1S8HNkicdk78aBeIJA1G1R/mLII5/n8MmH4M0JaYPcB/8yY1qQ1n/2xnN3PZ/ds8efy/d38kn0Njr6Rp6/R1TeONLjD+FS/kroYyLAe+EpJDYYnnSgfxQosqQflQcCTDehNQQWwPyOJt76RD/5Jp9mzRd0aVmF5sjTKJmzvZQgMo69yaYtKmhgr/UiDKoKedIRcp9V4HGsvwI1frjVlk2DaqHBeZu8SyyWQMmG16m0Tyy0oBz/Fuq16BaQbBHlRUOkVxVEjf92Bjf/+PyYbMFYGTNFmEJ0wozovxEZIRUXzbEdyIm1/lI5f2uM4aJ98UX8m5iL9z1U1zknBkB0p7LNyROOLz2MI1yczcDRgGXJGMwNvI1++3IP6npTxEb8x/RqrUuhdSi5ynGTGWRpc6Za9wpGUW+jGjBBs6fIhsINKOdIZsTE+ssXVh9nyknF0Re5Ds+XDZGHT6TBK8P7K4zhJ78ku5O8+XV+xp95UgLVtlNArN2HSYkwPOKe1LBtHB3UPqwdh+DEIONQ8Av7KvxIQDPW7EonEed1wOpx5xHipN523Gv4D7uJTtgSE1wjHCHu22C3JV1wjEoxDlH4ThEzHRfDbjcRhk2BqQVG/7ueAlxzOkWLdKyezDc5KHvRRN5jn5LjoDODwRNXKd/beJZajakuhfNnYghbeUNHRi3/mrk2HzJ1IKOKBwOw4sbhQQJc0t/iVXoES7BbMI7rbSD9f2FtMHDKOf3elaylvONUvcp6gpXTSj8NwMQKvZOmKeJBG5xP2mXeYDVwYuKAoCCfDe4XTiH/BdmloX7eqmp7l52/2PT7DAoGBnGyGsLTu9Yp6nXZzXvXrzqbxugkDbXuD682WUk5/FRjmhFVQCyR8ilT+aw4M7YVhUnIR5oEnhUU6ZthYpBHFpwsnIEQrqLFCgD0Cpo8hj0ITA2xGHgTgKz/VZvuJr2Hr0oFQYcQarYyl0VDBBjd97nYd0A47NDuF65bcKKYE9LUb+k30ta9t/szyu/c4Etjt3fXs5mY5+7hkb/Hf1fx6NvcrIoJ9Sd8/fG7pt3kJAAA='

Write-Embedded (Join-Path $internal 'Speech_CPU_CUDA.ps1') 'H4sIAAAAAAAC/61a+1PjSJL+nb+iwuNYWddIQMduz4Qd3m03GPAMDx8223NBM76yVbbVyJJHDx7D+H+/L6tKTwsY4paOxkaVlZWVzy+rtOYhX7V2GH5u/s091+GxGIm4ZczWibFrLORv7nmGeXsTxaHrL26b54EjWJfJx7tqajrUSxw3GPJ4SeNH7W/CXQhfRGwdBgss9C0WUczuXUcE0bdP/o+fFp9+Cm1+71b5jIIknIkjN3yBz2wpYpdFLj7DxF9EjOR2/W//nQjPE36V3RjLXgVB/E5uay9ZuP6EhK5y7D+KdJtbsq+FmC2HfHbHF6KOYPgULwO/SLBj7sy8aKfZD8Mg7M1iF8OhmItQ+DNJMYqDtbHTHJLAIooqgy62HHtPh4Efu34iQLjwgin32me90bj/62B8eHnUB+X+TjOK+WqNrycito6wS2YdB+GKx8x4ws/5ueNMTk9XqyiazOdzMMJqiRdHmPG5Ze7ME18Kx3pRJMK41cSSjktPdvPtnUNAbMxkz8yds5blQ+85IT2Ol2HwwFJCtmGbnPOV+D2BvlsZu+vQ2y3whuqcrgHxjd2bJY+WMZ964rZ5Krgjwqj7+XmTUx9DMV3DwJLSAE0eLuROnq9Dt0uMO5qf5ttJuaTsOmN3JYIkHolZ98eP+/udgoG6yigbyZo2Kpej7cl17IEvl5dPO/oZWQimGj+tIRdfrz13xonXXjCLYRDILfjKYIpnKOIk9NnAvw/uhHUFpSgp2WfitVPQ2YjfC+vnKPBzrZFz7jYvp9/FLE73fzO4tEma23b7a+jGoud5Y/EIK0rilqZmfzKIeQ/zjgPJlFlHYg1X/8e+udu6EA+WpqO59vX4+Ke+PwscrNpqzrkXCdM0i8Idu75jXfqiJFssQj8zC9wPkad8jPzycOl6ziAWK2adQcyQezLUCknBom3I3xhmxn/ZqyV3VbQakP8r4likYsIeE/uCr0AvF2Lp+mxjyvWVL8N+Wg5YKfFjZonf2YHJGifC5wlDOmBDfidiJsJ5EMI5YLsla2WbsRFS2LMj/DZrVniZdqNo0XTwZv8WimqKR4pi6UE6q0gnSjPMhgkoFU9+DlzfqmrCOBeOy0+TqXUYrNZJLKwLZGcbPMmN0q1R/lNTyxqlpeVz8kh2JvgcGy4ysvq/9tlcLL24Lakbb7LMK8AWY5oic/+exYkqY5zNaew01yo53i1SnZSyJWmGXKTGO8pZNdNa6n7M+C1V1USRXsEyCO/Jvf3hW8GBmqS4ZqSSeC5GKau/IkY5+78qhiK14sCiUKqV4wc2Ou19/McnFiE/RGweuhG8bgr3ni194TM4HCPP9Lj6/gUq5ihmC5Qxhhh+EOSRNvj8Qh48l+VXhE7Il2CI2OEygk6RSDvsjkii2EUFjdi1wCpYLBTuFAvdB9r/iZvWDs2CemTMUkDKv8vayNRoHyeep6Kw5y0CpJ/lSu/NtGnijkxJ1mkACRtaMyrgFFWbFVZtlKiVOavUrdfkyrzsTbnM8lpZUPy1dWSAvci4CVNElCOhxJtQLMQjUvM5JYdWQXMk3a4xuW/d/Da5/WCWfcQ07ZMwSNbRzcGtDQCXiCxCZeFNk267PYgusNXL8OsSAo7WfCZa6fqmCRBRUHkqlo8URwlv5SLHeVMe2kAEK2ggSqNCQkHKlAojwtE/F6GjmQfAZ0WMJ0V9Gl36YaNhv394ao0vLcCVcZsdDq/3Dq+Peuzi+uxscDEa987OeuPB5QVrXfSv+1fsAoDGZHKyISGMWEALvnMYeEHIDp+4X/YQqS2ZmLc90qzzJkm77SUVWgrlZFXOYKVx1EVVDqTSrO9I4czYZUaZj3Hq+g/CjdqMVITwYw+IUUTdVLgr6B/B7zNITR+9ZB6HfMEkVIWnLYTHKcSNzO6tK4AXzfhYJgwBEIG84HkSbCDEeQhW/2Kt73zv554JM+nSaPzW+pfb/s5NOBYzLqT5p2lKibEGlX+V9Oi3TO6oQiizQfjEdHHKwDbZBQj1T3aZxBY53w4qp+CybJJCJCOX6iFpJ4cDqr3ISNTTeeCh6OJ5oQxmKzWUVSdxALCOVNp8psmbyX3zWfvyZjJLHD53HzEmMfBGleRmqKpAmbFezNCDhiaVWBiUNxIACOf2s1ynK0XtgG2cRF3juDc4MzqKRVez6ggCjsCiCto1fb1Hn7Qin4DsKhPlpu/fu2HgrwAWEbpIMIUH/+ahS6C3ZZz3jwa90+svk8PL8+H1uD+5ur4YD877iD50CjPAa0NBnB/YyfDa6iXRA196EsF4i5jxJIJzeC7oJJhJKOUz5XepzYVf8p1ojUpjK4m9YPGCOVo6gY8DWdgoko+h+RH5XWabxofWm02IYX4w7Pgx1ttowvP9aBa6a7KCQptyIIb3Ke9JwfhL8ESZI29CJCiBOX3snMqqiyp7H4RLLuumqprlUthOmTQ0Tk+XpN1ciHh8OAR+9oVCv9ZZMMPaAQLzpx8/fWIWlIANn7kypq1CP8GqbVwupJHPnwpPIBLZcShWcCEqR+zBDR2dq6eCCj4itSDbX4nZNAq2QzblIo1njXMD6JnkBTXkFVPFYSKysWKG/F+/WAHSVGmPg+v1WoQtUyf5xgtJPmV5GKyf6tCYrL9HMLHrq9zXqonylyG0me8HjRrf8vhUbYY+KVgr2DfRxMa7bJCu8LINXtplHZopbjpl/SajOrj2KqNmJGKM6rY6e0w/VHdWfKLzb/egQzlv4oNnN8V3tDk6XLGk0RsdT0bFZAnP6BoHH3+09/HvwEifrxEFXYqC0jqw0yyRDfnnZ0fMOVL0RGXlljtX7qQQigQkz/JjQ6DkWQKVjdnBxwSBhqqJ7M2TODA6IJo44t6dCf1kU1pzlgU4Fg3F7wlsOQHdEgGsW/quSk8dZM7gYYJoDWIx+R5MIz2QM8y/ZX18yU0zJ0t1bX8HCQp0pvyMQaVujN5dN9LFqgWkWLRUJtDjqhWXgr4ztJj1NQjvIH4eCOk0MImi8TJM8rWT0KOjrmUcr9t7e5lvtMkd8jBrkhGfyrWBfoA7gDnc7n6HNV1moYgffJTfP3wwWdlt1e5GnhBrJGsBSzsROyiRSORLyiAc339EADmFgiJTss7DEvtJSiI7JPxbrBpZ6WLNZVcffLEG7XVvKdCZLRsdcuGlraCFcuPgDl6sNtqVebUzxR93G0DtmQRxz3WupcGhVpChzaHrRwI4kxUQqoG2UZesDdn89IYDIAhQzZaqI6ijHEKuuWjLYxP8/8NdwKxbQGKXpZCHYgwAQHa3gCXsF5VnCtybdNjX/c/0migvZwEg9sC/p5jw41bBy5fZSaLxq6UaB7kiZS6jW+nLOjmNWgAUJCg910lO75oCZg42xkt5ifBpOTHl1muStioeokpOtEdDDYIIUWxk0tdp4400k4asq+SdSKSXZhr6I5fGRaJEPycp5C+3YNkJcvU6QvlCGesD7JfO4XSddJ308K2KB7Z8RIYQFkybJ2b9U7ZPFccuSEPcLeA3KWd6mLcQ7GP+9Gb/Vul+RflpmUxtVUInKeAvkB5UScu9BrTTMnrX48tzNKijw1M0p70vp73+xcng5Jf+YDwanvUu2HH/9Kx/ddo7RnNrsA+sZksFFxSPa2hMONpl0ma74jIs9RndYiuvybj8wHqCDndUkFPYRmwh6CzHAeIXLFiTjjkcG1CEL/wgQsRKF1CZ4I8EMTy7swsMj2GZAjzeZXRg7S/YWka732HwFhhRdqpoVKN5IpZ0oaKOpoCNkBRTYrvg3Gqbxy6Wp9yd+9VwpJzHhiYAB2MIfmNo/Wd+quPqdqecn+H1zPJFhb2069snI9lZdXGyOl8xqxUj9cBX5kirVc1qVr1dPmbo+OVxHlWw2VKdQ2wLkQdAav6STKXDhcHF1/5g1FZ+IHkDDSw5vEMf+dUq1GZ9aUdtN0umdDJm2j761Mk7wJBwLevnYGrXnMT8jyD4U1OPmuS677Q4TUkhdvSyvTPOVUPJEWREddOQ02kbbd8b5DwnxXyVrbkVkCWSbElqgmmX2fI67jvM2JqQn5BoWCnPdz+3DOA45B9rlkw9HuHj4CO6/Oyh4/vbz7il05kaMusELKXQTFh9HJSdSfajGV+LXCaTrgnQ1eszV3mOT45bOjcYquydzmlsrb3ZelKsBDl/kcZEO9fnWw3hi5GxtWGySOHKZ98EOhpeV+KkIIxdNtrmPx+IJT+35dFNX8Yc8xM6pXBl6C3EA+VxHwEopdNx+s4oDPy5G65egRZ7zXJpNff0nAxzFIFSCQRt3oc4ZBbMEIdeZQvA6ucp5EB8SFjKVlS7lB6FTlESo5bPPl+Cq1L6ohxFFkUU+oCehdBhWWH6aaNKRyhJj9n6s/Z6Uo1J4PIK1NBkKTiZ2MCkU9KArC7UCmQjqn14qhlR7TLNKwwWklsWG2qx8mVoekvwVY5poAAnhaftcV3vX24KypO3Oo3mNEBLUzlFQMc8ieV1eQV2lajW/MkLuIPJro++ppufx3cUzCE4T9na6xromJ+Mzoo/TiKxoL446v5d/invJPFQtnzdT/udqeCrSeT+IboHnXvuTObyujnt3zcvnkLkZ8J1nVgTW+puX+pb16GrvYlOCZDf9AAFGbO+QDcwCqnoxQv6j/tM9tn0hohJX7OXDVjpZQMKsQ6bLXkYibibxHPrJ/hU/qoDo1cdKmeTcbAu7WDgdDO8gz9tspPrFEqyfu9DkqJfrZniOtvtqSRjBtCENThSdaXemRoSnIRM+5SGIG3NoVHE0mQY4VQilnS8p4j3NEma0PK5cxf4uJuxKO4u24mkyRp07FmV6xns4KFaOKjIUTKbCeHk36MI35zAF6jJz3qVF8Vr/NU0qgOEr106Z5qo24osn8pVdl7ErOVtvHMPrKH1Ly2GfDBbeqhdqncrcjbzB/JCpABjabNXUuSuplAbKCpdAzJKWxm18q10ZmoqPXmzndZyTJezYEYqf7DESD9En+S7UTE3ITIoseRClDjYargoi36kGvr88abuhJzSRpmzmmyXSMC97rFeQQ9pq5cpXtNCeQmliVQBSh3yzP9OUxR0suVDJVYoTgsqxbKgzXmEYJ08LF04aQh3bPyi6rTsMNSopUetvpwofaeOY03v/45+rsyRKgldfpe2yFyEoSdE2GbqfjdHaeIeX+kVQ40zRusQSEyUipiCYXmq04bJCoStKbZzpR6AnbeYVBRR5bXZPjvo/rVDpm3X0CzLLSssdiz7URGlDWE7E5i1RPhAV8pxYUKjPmsfno77V+l9v4y6yy/sS3807l0c9S/a6ta3kx0WpEvUwP2TUAi/fpHwjvt0Ny5fUatxJGn2N1nq+147vdcd9kYjZejspHWLVl3zAmb1H2dCLabfcqyVNL31knZSZ0RS3CK3OkGvdDHaMJkqvfLtpzpyrnZ75TvSLeernGfXd4olLcuXaJm8aC2ceSPpD1G603PvQdETij9/YzGP7u5czyN3Zntykp7C9sZs75h9/OffDurOEQtSUGP+Rl+5kbZ63nqJhyDNGm7rJ/5CKr3GaGajDsH9/29Z8sv+uouWt++vC+/WEcrjyEXyTvt1gCB9he7bqthAv9iwqbpz9KHLbtbRLIniYBVI9d82a8pyHl3mM6m1eE2cX2Mq9ht65TFKVisePnXf8fLAiYj4KpavKNCL2nH2Hge9H9Aw8zeVpcOseGyNVZPTS+JgBBCvJRnJjIo/RvSmqYLI1YsEJR0QsH6xldFbrm+vUHr1pypvO+Pb2IHOPqdBHv1ZbgfhhhmYBG6XSWdjZsfYMdtHfah5vRs9in5Z4NxFGNKFaSSvXzRCJv1W4JnNzoJFlB3IGuU3s3pnZ33Wux6d9L/2kJnG/Ys0bdNLWWOk7FGeuOtOHVQ2/T99LO0bYTAAAA=='

Write-Host "`n===== TESTSTART =====" -ForegroundColor Cyan
Write-Host 'GLiNER/SmolVLM2 verwenden die bisherigen echten CPU-/GPU-Testablaufe.'
Write-Host 'Speech-to-Text: echter CPU-/CUDA-API-Auftrag mit /plugins/plan, /jobs und /execute.'
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
        $mediaRoot=Join-Path $item.pluginRoot 'Testmedien'
        $media=Get-TestMedia $item.id $item.stagedPkg $mediaRoot
        if ($item.id -eq 'gliner') {
            $glinerBackend=if ($item.mode -eq 'gpu') {'cuda'} else {'cpu'}
            Run-Test "GLiNER $glinerBackend" (Join-Path $internal 'GLiNER_CPU_CUDA.ps1') @('-Root',$item.pluginRoot,'-Mode',$glinerBackend,'-GlinerPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
        } elseif ($item.id -eq 'smolvlm2') {
            Run-Test "SmolVLM2 $($item.mode)" (Join-Path $internal 'SmolVLM2_CPU_GPU.ps1') @('-Root',$item.pluginRoot,'-Mode',$item.mode,'-SmolPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython,'-VideoPath',$media.video)
        } else {
            Run-Test "Speech $($item.mode)" (Join-Path $internal 'Speech_CPU_CUDA.ps1') @('-Mode',$item.mode,'-AudioPath',$media.audio,'-TestRoot',$item.pluginRoot,'-ExePath',$item.stagedExe,'-SpeechPackage',$item.stagedPkg,'-PythonPackage',$item.stagedPython)
        }
        $results+= "$($item.id) $($item.mode): PASS - Installation und echte Inferenz/API"
    } catch {
        Write-Host "FEHLER: $_" -ForegroundColor Red
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
Write-Host "Version: $ProgrammVersion (Release 1.0.0 nach erfolgreichem Windows-Praxistest)"
Write-Host 'Keine bestehenden Testvarianten wurden geloescht oder ueberschrieben.'
