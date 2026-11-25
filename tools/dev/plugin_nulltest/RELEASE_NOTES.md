# MediaHub Plugin-Nulltest – naechster Release (Vorbereitung, 24.11.2026)

- Automatische Auswahl der hoechsten eindeutigen Nulltest-Version ohne zusaetzliche Steuerdatei; bei gleichnamiger Version in mehreren Varianten wird der Build sicher abgebrochen.
- `build_plugins.py` und `release_plugins.py` verwenden dieselbe Auswahl fuer ZIP, SHA256 und Verifikation.
- Generierte GitHub-Release-Notizen enthalten dynamisch die aktuelle Nulltest-Version, den Asset-Namen und die ausgewaehlte Skriptdatei; veraltete feste Angaben v1.0.0 entfernt.
- UTF-8-BOM-Fix und optionale `-DiagnoseAlle`-Protokollmarker dokumentiert. Interaktions-KI CPU und CUDA am 24.11.2026 erfolgreich end-to-end getestet; `-DiagnoseAlle` selbst noch nicht separat abgenommen.
- PowerShell-5.1-Syntax und Nulltest-ZIP-Build v1.0.25 am 24.11.2026 bestanden.
- CPU: native Node-/HTTPS-Tool-Calling-Pruefung bestanden; CUDA: drei Wiederholungen inklusive echtem CUDA-Backend-Nachweis und HTTPS bestanden.
- Beide Testlaeufe haben Ports 8766–8769 und temporaere Zugangsdaten bereinigt.
- Kein Release, Commit, Push oder Tag ausgefuehrt; keine Aenderungen am Raspberry-Pi-Installer.

---

# MediaHub Plugin-Nulltest – vorbereitete Aenderungen (24.11.2026)

- UTF-8-BOM-kompatible JSON-Konfiguration fuer native HTTPS-Tool-Calling-Probe aus erfolgreich getestetem Nulltest uebernommen.
- Optionaler Schalter `-DiagnoseAlle` mit datensparsamen, profilbezogenen Statusmarkern aus vorhandenen Logs; bestehende Testskripte und Erfolgskriterien unveraendert.
- `-DiagnosePause` bleibt CPU-Interaktions-KI-spezifisch; normale `-Mode all`-Pruefung einschliesslich nativer Tool-Calling-Tests bleibt erhalten.
- 24.11.2026: Interaktions-KI CPU v0.1.13 inklusive HTTPS-Tool-Calling und Bereinigung vom Benutzer als PASS bestaetigt.
- **Noch offen:** Windows-PowerShell-5.1-Syntaxpruefung und echter Test von `-DiagnoseAlle`; keine Freigabe als getesteter Gesamtstand.
- Kein Build, Commit, Push, Tag oder GitHub-Release.

---

# Nulltest v1.0.20 - aktuelle Uebernahme

- Aktuelle Skriptdatei: `MediaHub_Gemeinsamer_Nulltest_v1.0.20_Node_Auswahl.ps1`.
- Aus dem lokalen Sicherungsdateien-Ordner in den Plugin-Repository-Nulltest-Ordner uebernommen.
- Historische Release-Notizen bleiben unten erhalten; kein neuer Testdurchlauf behauptet.
- Der Build-/Release-Assistent muss darauf geprueft werden, ob er den aktuellen Nulltest statt v1.0.8 paketiert.

---

# MediaHub Plugin-Nulltest v1.0.8 – Release-Notizen

## Aenderungen seit v1.0.3

- Gemeinsames Testskript auf v1.0.8 aktualisiert, bisherigen v1.0.3-Skriptstand im ZIP ersetzt.
- Interaktions-KI v0.1.11 in den Nulltest aufgenommen: CPU/CUDA-Installation, echter Chat-Auftrag und API-Auswertung.
- Korrigierte Backend-Auswertung: technische Bestaetigung aus dem Worker-Ergebnis statt aus dem angeforderten Modus.
- Nach Testende Bereinigung ausschliesslich der zum Test gehoerenden Compute-Node-Prozessfamilie, einschliesslich `llama-server.exe`.
- Vorhandene sechs GLiNER-/SmolVLM2-/Speech-to-Text-Varianten sowie isolierte Plugin-Modellcaches beibehalten.
- README und Skriptname auf den aktuellen Stand gebracht.

## Testnachweis

- Interaktions-KI CPU: PASS, `owned_llama_process_cpu_mode_gpu_layers_0`, echte Chat-Antwort.
- Interaktions-KI CUDA: PASS, `llama_cpp_startup_log_offloaded_layers`, im llama.cpp-Log `offloaded 29/29 layers to GPU`, echte Chat-Antwort.
- Benutzer bestaetigte, dass die CMD-Fenster nach den Tests automatisch geschlossen wurden.
- Andere sechs Varianten wurden mit diesem Skriptstand nicht erneut vollstaendig getestet.

Kein Git-Push, kein GitHub-Release, keine Aenderung am Raspberry-Pi-Online-Installer. Separates Testwerkzeug, kein `.mhaiplugin`.
