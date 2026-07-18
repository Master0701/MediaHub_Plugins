# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 0.4.1**
- **MediaHub Metadata Editor 0.3.6**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub WebRemote 0.13.7**

# MediaHub Plugins – vollständiges Release

## MediaHub WebRemote v0.13.7

- Eigene Desktop-Weboberfläche bleibt über die normale Plugin-Verwaltung direkt öffnbar.
- WebRemote bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Browserbasierte Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben erhalten.

## MediaHub Mobile Dashboard v0.1.7

- Eigene mobile Oberfläche für Handy und Tablet bleibt direkt öffnbar.
- Mobile Dashboard bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Mobile Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben erhalten.

## MediaHub Metadata Editor v0.3.6

- Desktop- und Weboberfläche bleiben gemeinsam verfügbar.
- Der Metadata Editor bleibt in WebRemote und Mobile Dashboard als zusätzliche Plugin-Oberfläche sichtbar.
- Die Weboberfläche öffnet weiterhin in einem neuen Browser-Tab.

## MediaHub KI-Assistent v0.4.1

- KI-Assistent vollständig in den gemeinsamen Plugin-Build und Release aufgenommen.
- Web-Wissenssuche repariert und lokaler Wissensindex im Browser filterbar gemacht.
- Suchen nach Titeln, Aliasnamen und Beziehungen funktionieren direkt in der Weboberfläche.
- Werkzeuganforderungen für FFprobe, MediaInfo, Tesseract OCR und MKVToolNix werden strukturiert über `plugin.json` gemeldet.
- Erfordert MediaHub v1.0.15 mit zentraler Toolverwaltung und portabler Tool-Installation.

## Gemeinsamer Release-Stand

- Alle vier Plugins werden automatisch erkannt, validiert und vollständig neu gebaut.
- Für jedes Plugin werden eine `.mhplugin`-Datei und eine `.sha256`-Prüfsumme erzeugt.
- Der Plugin-Katalog wird beim Build automatisch aus den aktuellen Manifesten aktualisiert.

## Kompatibilität

- **MediaHub KI-Assistent 0.4.1** – mindestens MediaHub v1.0.15
- **MediaHub Metadata Editor 0.3.6** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
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
