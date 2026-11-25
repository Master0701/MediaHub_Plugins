> Teststatus 24.11.2026: Interaktions-KI v0.1.13 CPU und CUDA mit nativer Node-/HTTPS-Werkzeugrunde erfolgreich; CUDA in drei Wiederholungen. PowerShell-5.1-Syntax und Nulltest-Build bestanden. `-DiagnoseAlle` und andere Pluginprofile noch nicht neu vollstaendig abgenommen.

# MediaHub Plugin-Nulltest – aktueller Entwicklungsstand (24.11.2026)

**Aktive Testdatei:** `MediaHub_Gemeinsamer_Nulltest_v1.0.25_BOM_DiagnoseAlle.ps1`.
Der Build und Release-Assistent waehlen automatisch das einzige Nulltest-Skript mit der hoechsten Versionsnummer aus. Es ist keine Auswahl-Datei erforderlich. Falls mehrere Skripte dieselbe hoechste Version tragen, wird der Build aus Sicherheitsgruenden gestoppt; in diesem Fall nur die tatsaechlich aktuelle Variante im Nulltest-Ordner belassen.

**Erfolgreich getestet am 24.11.2026:** Interaktions-KI v0.1.13 CPU mit HTTPS, nativer Node-/HTTPS-Tool-Calling-Runde, simuliertem Temperaturwerkzeug und vollstaendiger Bereinigung. Das ist ein Testnachweis fuer die BOM-Fix-Variante; die neu erweiterte `-DiagnoseAlle`-Fassung ist noch nicht unter Windows PowerShell 5.1 end-to-end abgenommen.

**Testschalter:** `-DiagnosePause` testet ausschliesslich Interaktions-KI CPU und wartet vor der Bereinigung auf `JA`. `-DiagnoseAlle` ergaenzt Logmarker fuer die ausgefuehrten Profile, ersetzt aber weder die eigentlichen Tests noch die Pause. `-Mode all -DiagnoseAlle` startet alle acht CPU-/CUDA-Profile, nicht nur ioBroker. Ohne Pause bleibt die automatische Bereinigung aktiv.

**Release-Paket:** `python build_plugins.py nulltest` erzeugt `release/MediaHub_Plugin_Nulltest_v1.0.25.zip` und `.sha256` mit dem aktiven PS1 und diesem README. `release_plugins.py` verwendet dieselbe Auswahl und erzeugt dynamische Release-Notizen. Die separat bearbeitbare `native_tool_calling_probe.py` ist nicht als dritte Datei im ZIP enthalten, weil sie in der PS1 eingebettet ist; Quelle und Einbettung bei kuenftigen Aenderungen synchron halten.

**Noch zu pruefen:** PowerShell-5.1-Syntax, neuer `-DiagnoseAlle`-Ablauf, Release-Asset-Test ohne Git-Push. Ein GitHub-Release darf erst nach ausdruecklicher Freigabe stattfinden.

---

# MediaHub Nulltest – BOM-Fix und optionale Gesamtdiagnose (24.11.2026)

Aktuelle vorgeschlagene Hauptdatei: `MediaHub_Gemeinsamer_Nulltest_v1.0.25_BOM_DiagnoseAlle.ps1`.
Die bisherige v1.0.25 bleibt unveraendert. Die neue Datei basiert auf der vom Benutzer erfolgreich getesteten UTF-8-BOM-Fix-Fassung.

**Bestaetigt:** Interaktions-KI CPU v0.1.13, native Node-/HTTPS-Tool-Calling-Runde mit simuliertem Werkzeug, anschliessende Bereinigung PASS (24.11.2026). Die neue optionale Diagnose fuer alle Plugins wurde noch nicht unter Windows PowerShell 5.1 oder mit echten Installationen getestet.

- Normaler Aufruf ohne `-DiagnosePause` fuehrt auch die HTTPS-Tool-Calling-Probe aus (drei Wiederholungen) und bereinigt automatisch.
- `-DiagnosePause` bleibt auf Interaktions-KI CPU beschraenkt (eine Wiederholung; Bereinigung erst nach JA).
- **Neu:** `-DiagnoseAlle` kann mit `-Mode all`, `-Mode cpu` oder `-Mode gpu` kombiniert werden. Fuer jedes ausgefuehrte Profil wird eine datensparsame `DIAG_ALLE`-Zusammenfassung aus dem vorhandenen Startprotokoll erzeugt. Sie enthaelt nur Marker (true/false), Exitcode und Profilname, keine Rohantworten, Passwoerter oder API-Schluessel. Marker sind keine zusaetzlichen PASS-Beweise.
- Die eigentlichen GLiNER-, SmolVLM2- und Speech-Testskripte, ihre Startargumente, Erfolgsbedingungen und Bereinigungsablaeufe bleiben unveraendert. `-DiagnoseAlle` ist **keine** allgemeine Pausefunktion.
- `native_tool_calling_probe.py` als Entwicklungsquelle behalten; der Nulltest enthaelt die Probe bereits eingebettet. Beide muessen bei spaeteren Aenderungen synchron gehalten werden.

Beispiel (Windows PowerShell 5.1):

```powershell
cls
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\MediaHub_Gemeinsamer_Nulltest_v1.0.25_BOM_DiagnoseAlle.ps1" -Mode all -DiagnoseAlle
```

**Vor einem produktiven Ersatz:** PowerShell-5.1-Parser pruefen, dann mindestens einen kontrollierten Testlauf ausfuehren. Kein Build oder Release wurde erstellt.

---

# MediaHub Plugin-Nulltest v1.0.25

Aktueller Nulltest im Repository: `MediaHub_Gemeinsamer_Nulltest_v1.0.25_ToolCalling_Diagnose.ps1`.

## Start (Windows PowerShell)

```powershell
cls
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\MediaHub_Gemeinsamer_Nulltest_v1.0.25_ToolCalling_Diagnose.ps1"
```

Die jeweils unterstuetzten Parameter mit `Get-Help` bzw. im Skriptkopf kontrollieren. Dieses Testwerkzeug ist kein installierbares Plugin.

## Teststand

- Der Benutzer hat die vorherigen CPU-/CUDA- und HTTPS-Tests der Interaktions-KI erfolgreich durchgefuehrt.
- Diese Uebernahme allein ist **kein** neuer erfolgreicher Nulltest.
- Die bisherigen historischen Testergebnisse und Hinweise folgen unten.

---
# MediaHub Plugin-Nulltest v1.0.8 – Interaktions-KI und Prozessbereinigung

Eigenstaendiges Windows-PowerShell-5.1-Testwerkzeug fuer frische Plugin-Installationen und echte API-/Inferenzpruefungen. **Kein installierbares `.mhaiplugin`.**

## Umfang

- GLiNER, SmolVLM2 Vision, Speech-to-Text und Interaktions-KI: jeweils CPU- und GPU/CUDA-Profil (insgesamt acht Varianten).
- Interaktions-KI: echte Chat-API-Anfrage mit technischem Backend-Nachweis (`backend_used`, `backend_verified`, `evidence`). Der angeforderte Modus allein zaehlt nicht als Beweis.
- Interaktions-KI: selbst gestartete Compute-Node-Prozessfamilie wird am Testende bereinigt, einschliesslich des zugehoerigen `llama-server.exe`-Prozesses. Fremde Prozesse duerfen nicht beendet werden.
- Getrennte isolierte Modell-Caches pro Plugin/Testprofil unter `_Isolierte_Modellcaches`; die vorhandene Pfad-/Reparse-Point-Schutzlogik bleibt erhalten.

## Voraussetzungen

Windows PowerShell 5.1, Internet, freier Speicherplatz, Schreibrechte in einem separaten Testordner. CUDA benoetigt NVIDIA-GPU und funktionierenden Treiber. Die im Skript konfigurierten Projektpfade sind `D:\eigenes program\MediaHub-Plugins` und `D:\eigenes program\MediaHub-AI-Node`. Release-Pakete und Compute-Node-EXE werden aus den vorhandenen Projekt-Builds bezogen; bei Bedarf fragt das Skript nach einem Build.

## Start

ZIP entpacken, im Ordner `plugin_nulltest` PowerShell oeffnen und ausfuehren:

```powershell
cls; powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\MediaHub_Gemeinsamer_Nulltest_v1.0.8_Prozessbereinigung.ps1" -Mode all
```

`-Mode cpu` bzw. `-Mode gpu` beschraenkt die Profile. `-TestRoot "D:\Testordner"` waehlt einen separaten Testordner; ohne Parameter erfolgt eine Rueckfrage. `-VideoPath` kann eine Testvideodatei vorgeben.

**Achtung:** Alte isolierte Test-Caches der betreffenden Plugins koennen innerhalb des ausgewaehlten Testordners gezielt geloescht werden. Nicht auf Produktivordner zeigen. Das Skript erstellt keine GitHub-Releases und aendert den Raspberry-Pi-Online-Installer nicht.

## Teststand

- 31.10.2026: Historischer Test der urspruenglichen sechs Varianten: 6/6 PASS.
- 08.11.2026: Nulltest-Durchlauf 13, Interaktions-KI v0.1.11: CPU PASS, CUDA PASS, echte Chat-Inferenz und technischer Backend-Nachweis; der Benutzer bestaetigte, dass sich die CMD-Fenster wieder schliessen.
- Fuer die uebrigen sechs Varianten ist mit genau dieser Skriptversion kein erneuter Gesamt-Durchlauf dokumentiert.
# Native Tool-Calling-Abnahme (gemeinsamer Stand v1.0.25)

Grundlage ist die vom Benutzer bestaetigte Datei unter
`D:\eigenes program\cheti sicherungs datein\2-1\Neuer Ordner\MediaHub_Gemeinsamer_Nulltest_v1.0.25_ToolCalling_Diagnose.ps1`.
Die zusammengefuehrte startbare Datei liegt hier im Repository; die Grundlage bleibt unveraendert.

Alle v1.0.25-Ablaufe fuer Installation, EXE-Auswahl, Benutzer-Einrichtung,
HTTPS-Anmeldung, API-Aktivierung/Schluessel/Modellliste, Firewall, CPU/CUDA,
Prozessbereinigung und Gesamtfehlerstatus bleiben erhalten. Die anderen
Plugin-Testskripte und Python-Setup-Helfer sind inhaltlich unveraendert.

Die bisherige einzelne HTTPS-Required-Probe wird durch eine gemeinsame native
Probe fuer Node und HTTPS ersetzt. Je drei Wiederholungen pruefen Required,
Named, None, Auto, normalen Chat und die Verarbeitung des ausschliesslich lokal
simulierten Messwerts 21,5 Grad Celsius. Keine echten ioBroker-Geraete werden
angesprochen. Jede Node-Antwort muss Worker-ID, backend_used, backend_verified
und evidence nachweisen; nach HTTPS wird das Backend erneut geprueft.

`native_tool_calling_probe.py` bleibt die bearbeitbare, isoliert getestete
Entwicklungsquelle und ist bytegleich im PS1 eingebettet. Zum Start ist allein
das gemeinsame PS1 erforderlich. Die Probe laeuft vor der bestehenden
API-Deaktivierung und Prozess-/Firewallbereinigung. Der API-Key wird ueber stdin
uebergeben, nicht als Prozessargument oder Datei. Die selbstsignierte
HTTPS-Testverbindung behaelt die isolierte v1.0.25-Zertifikatspolitik bei;
manuelle HTTPS-Proben validieren weiterhin das Zertifikat.

Start fuer beide Profile:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\eigenes program\MediaHub-Plugins\tools\dev\plugin_nulltest\MediaHub_Gemeinsamer_Nulltest_v1.0.25_ToolCalling_Diagnose.ps1" -Mode all
```

Der Test fragt nach dem separaten Testordner und der Compute-Node-EXE.
Interaktions-KI v0.1.13 wird aus dem lokalen release-Ordner bezogen.
Die ausgewaehlte Compute-Node-EXE muss den HTTPS-/API-Schluessel-Stand enthalten.
Die Vorbereitung ist kein Nachweis einer erfolgreichen echten CPU-/GPU-Inferenz;
den vollstaendigen Nulltest startet der Benutzer anschliessend selbst.

## Gezielte Fehlerdiagnose (24.11.2026)

Die Probe protokolliert ausschliesslich feste Diagnosefelder: Transport,
Teilpruefung/Wiederholung, HTTP-Status, Jobstatus, erlaubte finish_reason-Werte,
Tool-Anzahl, bekannten Testwerkzeugnamen, Schema-Ergebnis und Uebergabe/Verarbeitung
der simulierten 21,5 Grad. Fremde Namen, Antworttexte, Argumentwerte, Zugangsdaten
und rohe Fehlermeldungen werden nicht ausgegeben. Vom Plugin verworfene Rohantworten
sind am Node-/HTTPS-Endpunkt nicht verfuegbar; die Probe kennzeichnet dies explizit.

Nur gegen eine bereits laufende isolierte CPU-Test-Node (keine Installation):

```powershell
python -B "D:\eigenes program\MediaHub-Plugins\tools\dev\plugin_nulltest\native_tool_calling_probe.py" --backend cpu --node-no-auth --repetitions 1
```

`--node-no-auth` nur bei der isolierten Node mit deaktivierter Node-Authentifizierung
verwenden. Sonst weglassen; das Token wird verdeckt abgefragt. Fuer HTTPS zusaetzlich
`--api-url "https://<Node-IP>:8769/v1" --ca-file "<Zertifikat.pem>"` angeben;
der API-Key wird verdeckt abgefragt. Der gemeinsame Nulltest nutzt weiterhin seine
bereits vorhandene isolierte HTTPS-Konfiguration und Bereinigung.

Bei verworfener Modellantwort separat den bereits laufenden llama-server pruefen:

```powershell
python -B "D:\eigenes program\MediaHub-Plugins\tools\dev\plugin_nulltest\native_tool_calling_probe.py" --backend cpu --direct-llama --repetitions 1
```

Diese Direktprobe zeigt die Rohantwort-Metadaten ohne Inhalte, umgeht Plugin und
Web-Bridge und gilt nicht als CPU-/CUDA-Backend-Nachweis. Sie uebertraegt dieselben
Testwerkzeuge und Named-zu-Required-Abbildung, aber nicht den vom Plugin ergaenzten
Systemprompt. Ein Erfolg beweist deshalb nicht den Erfolg des gesamten Plugin-Pfads.
Nach abgeschlossener Bereinigung sind die Dienste gestoppt; die Probe startet sie
nicht selbst. Fuer CUDA bei bereits entsprechend gestarteter Node `--backend cuda`.

## Optionaler CPU-Diagnoselauf mit Pause

`-DiagnosePause` beschraenkt die Auswahl auf Interaktions-KI und erzwingt CPU,
auch wenn `-Mode all` oder `-Mode gpu` angegeben ist. Die vorhandenen
Installations-, Chat-, Backend-, HTTPS- und API-Pruefungen laufen weiter.
Die native Node-/HTTPS-Probe wird mit einer Wiederholung ausgefuehrt.
Danach wartet der Test auch bei einem Werkzeugfehler auf die Eingabe `JA`.
Bis dahin bleiben Node, llama-server, API und Test-Firewall fuer weitere
Pruefungen verfuegbar. Das vorhandene Startprotokoll enthaelt die DIAG-Ausgaben.
Erst `JA` fuehrt zur bisherigen Bereinigung; ein Fehler bleibt ein Fehler.
Bei frueherem Abbruch wird ebenfalls pausiert, sofern die eigene Node noch laeuft.
Ohne `-DiagnosePause` bleiben Auswahl, drei Wiederholungen und automatische
Bereinigung unveraendert. Das Diagnosefenster geoeffnet lassen und weitere
Pruefungen in einem zweiten PowerShell-Fenster ausfuehren.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\eigenes program\MediaHub-Plugins\tools\dev\plugin_nulltest\MediaHub_Gemeinsamer_Nulltest_v1.0.25_ToolCalling_Diagnose.ps1" -DiagnosePause
```
