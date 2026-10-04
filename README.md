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
- **MediaHub GLiNER 0.1.0**
- **MediaHub AI Test Provider 1.0.0**
- **MediaHub SmolVLM2 Vision 0.1.0**
- **MediaHub Speech-to-Text 0.1.2**

# MediaHub Plugins v0.5.19 – vollständiges Release

## MediaHub KI-Assistent v7.0.11

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Audio Metadata Editor v0.0.1

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Metadata Editor v0.4.5

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Smart Renamer v0.5.18

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub GLiNER v0.1.0

- Neues AI-Node-Plugin für lokale semantische Entitäts- und Identitätserkennung.
- Stellt die Capability `semantic_text_analysis` für den MediaHub-KI-Assistenten bereit.
- Unterstützt die gemeinsame GLiNER-Runtime aus dem MediaHub-Tools-Repository.
- Unterstützt Windows Compute Node sowie Linux ARM64 / Raspberry Pi über die gemeinsame Runtime-Verwaltung.
- Runtime und Modell werden nicht unnötig im Plugin-Paket gebündelt, sondern über die vorgesehene Tool-/Runtime-Verwaltung bereitgestellt.

## MediaHub AI Test Provider v1.0.0

- Unveränderter AI-Node-Plugin-Stand in diesem Release.

## MediaHub SmolVLM2 Vision v0.1.0

- Neues AI-Node-Plugin für lokale Bild-, Vision- und Video-Frame-Analyse.
- Unterstützt MediaHub AI Nodes und Windows Compute Nodes.
- Verwendet SmolVLM2-500M-Video-Instruct über die gemeinsame MediaHub-Tools-Modellverwaltung.
- Unterstützung für Video-Frame-Analyse und kontrollierte Frame-Verarbeitung ergänzt.
- Das für die Video-Frame-Verarbeitung benötigte FFmpeg wird bewusst direkt im Plugin-Paket mitgeliefert.
- Modellbereitstellung, Runtime-Status und Runtime-Provisionierung sind in die Plugin-Infrastruktur integriert.
- Große Modelldateien werden nicht im Plugin-Paket gebündelt, sondern über die vorgesehene Tool-/Modellverwaltung bereitgestellt.

## MediaHub Speech-to-Text v0.1.2

- Unveränderter AI-Node-Plugin-Stand in diesem Release.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.

## Kompatibilität

- **MediaHub KI-Assistent 7.0.11** – mindestens MediaHub v1.0.17
- **MediaHub Audio Metadata Editor 0.0.1** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.4.5** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.18** – mindestens MediaHub v1.0.18
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5
- **MediaHub GLiNER 0.1.0** – AI-Node API 1
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1
- **MediaHub SmolVLM2 Vision 0.1.0** – AI-Node API 1
- **MediaHub Speech-to-Text 0.1.2** – AI-Node API 1

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
