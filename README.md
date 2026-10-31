# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 7.0.11**
- **MediaHub Audio Metadata Editor 0.0.1**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.4.5**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.5.18**
- **MediaHub WebRemote 0.13.7**
- **MediaHub GLiNER 0.1.3**
- **MediaHub AI Test Provider 1.0.0**
- **MediaHub Python Runtime 0.1.3**
- **MediaHub SmolVLM2 Vision 0.1.3**
- **MediaHub Speech-to-Text 0.1.3**

# MediaHub Plugins v0.5.30 – vollständiges Release

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

- 102 Python-Haupttests bestanden; fünf zusätzliche Plugin-Testsuiten erfolgreich (Windows, 31.10.2026).
- Zwölf Plugin-Pakete gebaut (sieben MediaHub, fünf AI-Node), einschließlich Entwicklungs-Paket Listen & Export v0.0.0.
- Veröffentlichbare Plugins erhalten `.mhplugin`- bzw. `.mhaiplugin`-Pakete mit SHA256-Dateien.
- Listen & Export v0.0.0 bleibt im Katalog und Gesamtbuild, wird aber gemäß Release-Regel nicht als GitHub-Plugin-Asset hochgeladen.
- Beide Plugin-Kataloge wurden im Gesamtbuild aktualisiert.

## Zusatzwerkzeug: MediaHub Plugin-Nulltest v1.0.0

- Separates ZIP-Asset `MediaHub_Plugin_Nulltest_v1.0.0.zip` mit SHA256-Prüfsumme.
- GLiNER, SmolVLM2 und Speech-to-Text: CPU- und CUDA-Nullinstallationen mit echten API-/Inferenztests.
- Windows PowerShell 5.1, Internetzugang und für GPU-Tests eine NVIDIA-GPU erforderlich.
- Dieses Diagnosewerkzeug ist kein installierbares Plugin.

## Kompatibilität

- **MediaHub KI-Assistent 7.0.11** – mindestens MediaHub v1.0.17
- **MediaHub Audio Metadata Editor 0.0.1** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.4.5** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.18** – mindestens MediaHub v1.0.18
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5
- **MediaHub GLiNER 0.1.3** – AI-Node API 1
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1
- **MediaHub Python Runtime 0.1.3** – AI-Node API 1
- **MediaHub SmolVLM2 Vision 0.1.3** – AI-Node API 1
- **MediaHub Speech-to-Text 0.1.3** – AI-Node API 1

## Projektaufbau

- `plugins/` – MediaHub-Plugins (`.mhplugin`)
- `ai_node_plugins/` – AI-Node-/Raspberry-Pi-Plugins (`.mhaiplugin`)
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – Plugin-Store- und Updatekataloge
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `tools/dev/` – dauerhaft nützliche Entwickler- und Diagnosetools
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Release ausführen

Lokaler Prüflauf ohne Veröffentlichung:

```powershell
release_plugins.cmd -Tag v0.5.5 -NoPush
```

Vollständiges Release:

```powershell
release_plugins.cmd -Tag v0.5.5
```

Alle Versions- und Paketnamen werden automatisch aus den jeweiligen
`plugins/*/plugin.json` und `ai_node_plugins/*/plugin.json` übernommen.
