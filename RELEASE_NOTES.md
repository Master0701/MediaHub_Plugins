# MediaHub Plugins v0.5.33 – vollständiges Release

## MediaHub KI-Assistent v7.0.11

- Lokaler MediaHub-KI-Assistent mit intelligenter Medienerkennung, In-Video- und Speech-Analyse, Semantic Identity Pipeline, Knowledge Graph, bestätigtem Lernen und neuer Lernroutine mit Review, manueller Korrektur, Lernhistorie und fallgenauem Rückgängig-System.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub Audio Metadata Editor v0.0.1

- Audio-Metadaten-Editor für allgemeine Audiodateien und Hörbücher. Der allgemeine Audio-Bereich und der spezialisierte Hörbuch-Bereich verwenden dieselbe Audio-Metadaten-Engine, Tool-Infrastruktur und Sicherheitslogik.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub Listen & Export v0.0.0

- Entwicklungsstand 0.0.0: im Katalog geführt, nicht als GitHub-Release-Plugin veröffentlicht.

## MediaHub Metadata Editor v0.4.5

- Lokaler Medienbrowser mit Metadaten-, NFO- und Bildeditor, Ordnerauswahl und integrierter Poster-Vorschau.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub Mobile Dashboard v0.1.7

- Mobile MediaHub-Oberfläche für Handy und Tablet mit einklappbarer linker Sidebar, QR-Code und Geräte-Kopplung.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub Smart Renamer v0.5.18

- Smart Renamer mit Review-Priorisierung, Konfliktgewichtung und prioritätsbasierter Sortierung in Web/Desktop.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub WebRemote v0.13.7

- Lokales MediaHub Desktop-Control-Center für PC und Notebook mit vollständigem Web-Assistenten und Live-Downloads.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub GLiNER v0.1.3

- GLiNER für Windows Compute Node und Raspberry Pi mit isolierter Runtime und kontrollierter Bereitstellung.
- Frische CPU- und CUDA-Nullinstallationen unter Windows mit echter GLiNER-Modellinferenz getestet.
- Private Python-3.12.10-Laufzeit und CPU-/CUDA-PyTorch-Profile geprüft.
- Runtime-Bereitschaft wird vor Analyseaufträgen geprüft; keine stillschweigende Installation durch Worker.

## MediaHub Interaktions-KI v0.1.13

- Bestaetigtes CPU-/CUDA-Profil wird nach erfolgreicher lokaler Runtime-/Modellinstallation gespeichert.
- Lokaler llama.cpp-Server kann bei Chat-Auftraegen anhand der gespeicherten Freigabe automatisch gestartet werden.
- Runtime-Pfad aus Plugin-Kontext; korrekt gekennzeichnete verwaltete Installation.
- Keine stillschweigenden Downloads und kein Start fuer LAN-/Remote-Endpunkte.
- CPU- und CUDA-Nulltest mit echter Inferenz sowie nativem Node-/HTTPS-Tool-Calling am 24.11.2026 bestanden.

## MediaHub AI Test Provider v1.0.0

- Test-Plugin für die komplette MediaHub-AI-Node-Installationskette.
- Plugin-Version unverändert; im aktuellen Windows-Gesamtbuild erfolgreich paketiert.

## MediaHub Python Runtime v0.1.3

- Gemeinsame portable Python-Runtime v0.1.3 als eigenständiges Windows-Compute-Node-Plugin.
- Kontrollierte Python-Bereitstellung mit SHA256-/Manifestprüfung, sicherer Entpackung und Schutz vorhandener Installationen.
- Pluginübergreifende Runtime-Nutzung für GLiNER, SmolVLM2 und Speech-to-Text vorbereitet.
- Kein automatischer Download allein beim Plugin-Start.

## MediaHub SmolVLM2 Vision v0.1.3

- SmolVLM2 v0.1.3 mit korrigierter CPU-/CUDA-Erkennung und isolierten Runtime-Pfaden.
- Echte CPU- und CUDA-Modellinferenz in separaten Nullinstallationen getestet.
- FFmpeg und FFprobe werden für die Video-Frame-Verarbeitung im Plugin-Paket mitgeliefert.
- Gemeinsame Python-Runtime und getrennte Plugin-Abhängigkeiten berücksichtigt.

## MediaHub Speech-to-Text v0.1.3

- Speech-to-Text v0.1.3 mit isolierter faster-whisper-Laufzeit.
- Runtime-Anbindung für den gemeinsamen Python-Runtime-Provider und getrennte Plugin-Umgebung weiterentwickelt.
- Paketbau und Windows-Tests erfolgreich; frühere echte CPU-Transkription auf Raspberry Pi dokumentiert.
- Keine unbelegte Aussage über eine erneute vollständige Windows-Nullinstallation.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.

## Gemeinsamer Build- und Teststand

- Aktueller Gesamtbuild vom 25.11.2026: `python -B build_plugins.py all` erfolgreich abgeschlossen; 13 Plugin-Pakete erstellt (7 MediaHub, 6 AI-Node), jeweils mit SHA256-Datei.
- Beide Plugin-Kataloge wurden im aktuellen Gesamtbuild aktualisiert.
- Zusätzlich `MediaHub_Plugin_Nulltest_v1.0.25.zip` mit SHA256-Datei erstellt.
- Python-Syntaxprüfung von `build_plugins.py` und `release_plugins.py` erfolgreich; `git diff --check` ohne Fehler (nur Zeilenenden-Warnungen).
- Release-Assistent `--dry-run --tag v0.5.33` erfolgreich: generierte GitHub-Release-Beschreibung, bestehende Artefakte und Nulltest-Prüfsumme geprüft; kein Commit, Tag, Push oder Release.
- Historischer Teststand vom 31.10.2026: 102 Python-Haupttests bestanden; fünf zusätzliche Plugin-Testsuiten erfolgreich.
- Historischer Gesamtbuild vom 31.10.2026: zwölf Plugin-Pakete (7 MediaHub, 5 AI-Node), einschließlich Listen & Export v0.0.0.
- Listen & Export v0.0.0 bleibt Entwicklungsstand und darf nicht als GitHub-Plugin-Asset hochgeladen werden.
- Ein vollständiger erneuter Mehrplugin-Nulltest sowie die gesonderte Abnahme von `-DiagnoseAlle` stehen weiterhin aus.

## Zusatzwerkzeug: MediaHub Plugin-Nulltest v1.0.25

- Separates ZIP-Asset `MediaHub_Plugin_Nulltest_v1.0.25.zip` mit SHA256-Pruefsumme.
- Enthaltenes Testskript: `MediaHub_Gemeinsamer_Nulltest_v1.0.25_BOM_DiagnoseAlle.ps1`.
- GLiNER, SmolVLM2, Speech-to-Text und Interaktions-KI: CPU-/CUDA-Testprofile.
- Interaktions-KI: native Node-/HTTPS-Tool-Calling-Pruefung mit simuliertem Werkzeug; keine echten ioBroker-Geraete.
- `-DiagnosePause` fuer isolierte Interaktions-KI CPU; `-DiagnoseAlle` fuer zusaetzliche Protokollmarker (noch separat abzunehmen).
- Interaktions-KI v0.1.13: CPU und CUDA am 24.11.2026 mit echter Inferenz sowie nativem Node-/HTTPS-Tool-Calling bestanden (CPU einmal, CUDA drei Wiederholungen).
- Windows-PowerShell-5.1-Syntax und Nulltest-ZIP-Build v1.0.25 am 24.11.2026 bestanden; vollstaendiger Mehrplugin-Test noch offen.
- Windows PowerShell 5.1, Internetzugang und fuer GPU-Tests eine NVIDIA-GPU erforderlich.
- Dieses Diagnosewerkzeug ist kein installierbares Plugin.
