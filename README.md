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
- **MediaHub AI Test Provider 1.0.0**
- **MediaHub Speech-to-Text 0.1.2**

# MediaHub Plugins v0.5.18 – vollständiges Release

## MediaHub KI-Assistent v7.0.11

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Audio Metadata Editor v0.0.1

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Metadata Editor v0.4.5

- Bestätigter Rename-Handoff zum MediaHub Smart Renamer ergänzt.
- Der Handoff wird ausschließlich nach bestätigter Medienidentität aus der menschlichen GUI-Bestätigung ausgelöst.
- Fehlt der Smart Renamer oder seine Handoff-Capability, wird der Metadata-Write-Vorgang sauber fortgesetzt und der Rename-Handoff übersprungen.
- Der Medienpfad und die bestätigten Metadaten werden kontrolliert an den Smart Renamer übergeben.
- Fehler im Rename-Handoff werden strukturiert an das Ergebnis des Metadata-Write-Vorgangs angehängt.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Smart Renamer v0.5.18

- Neue Runtime-Capability `rename.metadata_handoff` für die Zusammenarbeit mit dem Metadata Editor ergänzt.
- Bestätigte Metadata-Editor-Ergebnisse können jetzt über die bestehende Vorschau-, Rename-Plan-, Bestätigungs- und Transaktionspipeline ausgeführt werden.
- Automatische Ausführung ist nur bei ausdrücklich bestätigtem Metadata-Editor-Handoff erlaubt.
- Nicht ausführbare oder prüfpflichtige Rename-Pläne werden nicht automatisch ausgeführt.
- Fehlende bestätigte Metadaten oder leere Handoff-Dateilisten werden abgewiesen.
- Neue Tests für Bestätigungspflicht, sichere Transaktionsausführung, blockierte Pläne, fehlende Metadaten und Capability-Vertrag ergänzt.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub AI Test Provider v1.0.0

- Unveränderter AI-Node-Plugin-Stand in diesem Release.

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
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1
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
