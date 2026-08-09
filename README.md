# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 7.0.5**
- **MediaHub Hörbuchverwaltung 0.0.0**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.3.6**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.5.16**
- **MediaHub WebRemote 0.13.7**
- **MediaHub AI Test Provider 1.0.0**

# MediaHub Plugins v0.5.10 – vollständiges Release

## MediaHub KI-Assistent v7.0.5

- Unveränderter Plugin-Stand in diesem Infrastruktur-Release.
- Wird weiterhin als manuell zu installierendes MediaHub-Plugin geführt.

## MediaHub Metadata Editor v0.3.6

- Zentraler lokaler Medienbrowser mit Metadaten-, NFO- und Bildeditor, Live-Vergleich und automatischen Sicherungen.

## MediaHub Mobile Dashboard v0.1.7

- Mobile MediaHub-Oberfläche für Handy und Tablet mit einklappbarer linker Sidebar, QR-Code und Geräte-Kopplung.

## MediaHub Smart Renamer v0.5.16

- Windows-Smart-Renamer mit gemeinsamer Desktop-, WebRemote- und Mobile-Oberfläche, stabiler v0.4.0-Darstellung, eingebetteten Profilen und sicherer Live-Vorschau.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Infrastruktur-Release.

## MediaHub AI Test Provider v1.0.0

- Erstmalige Aufnahme als AI-Node-/Raspberry-Pi-Plugin unter `ai_node_plugins/`.
- Wird als `.mhaiplugin` gebaut und gemeinsam mit den normalen MediaHub-Plugins veröffentlicht.
- Dient als Testplugin für die neue AI-Node-Plugin-Infrastruktur.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.

## Kompatibilität

- **MediaHub KI-Assistent 7.0.5** – mindestens MediaHub v1.0.17
- **MediaHub Hörbuchverwaltung 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.3.6** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.16** – mindestens MediaHub v1.0.18
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1

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
