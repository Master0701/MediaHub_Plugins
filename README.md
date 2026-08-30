# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 7.0.8**
- **MediaHub Audio Metadata Editor 0.0.1**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.4.4**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.5.17**
- **MediaHub WebRemote 0.13.7**
- **MediaHub AI Test Provider 1.0.0**
- **MediaHub Speech-to-Text 0.1.1**

# MediaHub Plugins v0.5.14 – vollständiges Release

## MediaHub KI-Assistent v7.0.8

- Funktionsstand dieses Releases unverändert.
- Unfertige lokale KI-Entwicklungsarbeiten sind nicht Bestandteil dieses Releases.

## MediaHub Audio Metadata Editor v0.0.1

- Funktionsstand unverändert.

## MediaHub Metadata Editor v0.4.4

- Funktionsstand unverändert.

## MediaHub Mobile Dashboard v0.1.7

- Funktionsstand unverändert.

## MediaHub Smart Renamer v0.5.17

- Funktionsstand unverändert.

## MediaHub WebRemote v0.13.7

- Funktionsstand unverändert.

## MediaHub AI Test Provider v1.0.0

- AI-Node-Plugin.
- Funktionsstand unverändert.

## MediaHub Speech-to-Text v0.1.1

- Neues gemeinsames AI-Node-/Compute-Node-Worker-Plugin für lokale Speech-to-Text-Ausführung.
- Unterstützt Raspberry Pi / Linux ARM64 und Windows Compute Node / Windows AMD64.
- Verwendet eine isolierte `faster-whisper`-Laufzeit statt der zentralen MediaHub- bzw. AI-Node-Python-Umgebung.
- Unterstützt CPU- und GPU-Ausführung sowie automatische Backend-Auswahl.
- Raspberry-Pi-Ausführung mit realer Videodatei erfolgreich geprüft.
- Windows-Compute-Node-Ausführung mit NVIDIA CUDA und realer Videodatei erfolgreich geprüft.
- Worker-Status ermittelt die Verfügbarkeit von `faster-whisper` jetzt aus der isolierten Plugin-Laufzeit.
- Behebt dadurch die falsche Anzeige `engine.available = false` bei bereits einsatzbereiter isolierter Laufzeit.
- Paket enthält README, Changelog, Lizenz und Requirements-Datei.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.

## Kompatibilität

- **MediaHub KI-Assistent 7.0.8** – mindestens MediaHub v1.0.17
- **MediaHub Audio Metadata Editor 0.0.1** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.4.4** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.17** – mindestens MediaHub v1.0.18
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1
- **MediaHub Speech-to-Text 0.1.1** – AI-Node API 1

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
