# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub Metadata Editor 0.2.0**
- **MediaHub Mobile Dashboard 0.1.5**
- **MediaHub WebRemote 0.13.5**

# MediaHub Plugins – Metadata Editor v0.2.0

## Enthaltene Plugins

### MediaHub Metadata Editor v0.2.0

- NFO-Dateien erkennen und UTF-8-sicher anzeigen
- NFO-Dateien aus den bearbeiteten Metadaten neu erstellen oder aktualisieren
- automatische Sicherung vorhandener NFO-Dateien vor jeder Änderung
- Poster, Fanart, Banner und Thumbnail erkennen und über lokale Dateipfade ersetzen
- automatische Sicherung ersetzter Bilder
- nicht als UTF-8 lesbare oder fehlerhafte NFO-Dateien werden nicht überschrieben
- sichere Entwürfe und Vergleichsansicht bleiben erhalten

### MediaHub Mobile Dashboard v0.1.5

- unverändert enthalten
- mobile Oberfläche für Handy und Tablet

### MediaHub WebRemote v0.13.5

- unverändert enthalten
- Desktop-Weboberfläche für PC und Notebook

## Gemeinsame Änderungen

- Plugin-Katalog auf Metadata Editor v0.2.0 aktualisiert
- alle Text-, JSON- und XML-Ausgaben UTF-8-sicher
- alle drei Plugins bleiben unabhängig installierbar

## Kompatibilität

Die aktuellen Plugins benötigen mindestens **MediaHub v1.0.5**.

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
