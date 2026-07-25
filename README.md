# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 1.0.0**
- **MediaHub Hörbuchverwaltung 0.0.0**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.3.6**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.0.0**
- **MediaHub WebRemote 0.13.7**

﻿# MediaHub Plugins v0.5.5 – vollständiges Release

## MediaHub WebRemote v0.13.7

- Lokale Desktop-Weboberfläche für PC und Notebook.
- Browserbasierte Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben verfügbar.
- WebRemote bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.

## MediaHub Mobile Dashboard v0.1.7

- Mobile Oberfläche für Handy und Tablet.
- Einklappbare linke Sidebar und Geräte-Kopplung bleiben verfügbar.
- Mobile Dashboard bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.

## MediaHub Metadata Editor v0.3.6

- Desktop- und Weboberfläche bleiben gemeinsam verfügbar.
- Bearbeitung von Metadaten, NFO-Dateien und Medienbildern.
- Integration als zusätzliche Oberfläche in WebRemote und Mobile Dashboard.

## MediaHub KI-Assistent v1.0.0

- Mehrstufige Medienerkennung mit Supervisor-Agent.
- OCR-, Audio-, Frame-, Szenen-, Untertitel- und Fingerprint-Agenten.
- Erklärbare Decision Engine zur Bewertung widersprüchlicher Erkennungsergebnisse.
- Lokale Fingerprint-Referenzdatenbank.
- Qualitätsbewertung und Referenzvergleich.
- TMDb-, TVDb- und Wikipedia-Provider.
- Quellenverwaltung und Online-Ergebnisbewertung.
- Analyse-Cache und zentrale Werkzeugerkennung.
- Übergabe-API für Metadata Editor und Smart Renamer.
- Gemeinsame lokale Weboberflächen-Basis integriert.
- Erfordert mindestens MediaHub v1.0.15.

## Gemeinsamer Release-Stand

- Alle vier veröffentlichten Plugins wurden vollständig neu gebaut.
- Für jedes Plugin stehen eine `.mhplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Der Plugin-Katalog wird aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 werden nicht als installierbare Pakete veröffentlicht.

## Kompatibilität

- **MediaHub KI-Assistent 1.0.0** – mindestens MediaHub v1.0.15
- **MediaHub Hörbuchverwaltung 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.3.6** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5

## Projektaufbau

- `plugins/` – getrennte, einzeln installierbare Plugins
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – zukünftiger Download- und Updatekatalog
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Plugins bauen

Alle Plugins sauber neu erstellen:

```powershell
python build_plugins.py all --clean
```

Nur WebRemote erstellen:

```powershell
python build_plugins.py web_remote --clean
```

Die fertigen `.mhplugin`-Dateien und `.sha256`-Prüfsummen liegen anschließend unter `release/`.

## Release vorbereiten

```powershell
python prepare_plugin_release.py
```

Dieser Befehl übernimmt `RELEASE_NOTES_PENDING.md` in die verfolgte Datei
`RELEASE_NOTES.md` und aktualisiert diese README. Die temporäre Pending-Datei
bleibt lokal und wird nicht in Git aufgenommen.
