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
