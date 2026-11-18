# MediaHub Plugin-Nulltest v1.0.20

Aktueller Nulltest im Repository: `MediaHub_Gemeinsamer_Nulltest_v1.0.20_Node_Auswahl.ps1`.

## Start (Windows PowerShell)

```powershell
cls
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\MediaHub_Gemeinsamer_Nulltest_v1.0.20_Node_Auswahl.ps1"
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
