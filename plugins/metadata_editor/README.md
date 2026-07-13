# MediaHub Metadata Editor 0.2.0

Der Metadata Editor verwaltet Bibliotheksmetadaten, lokale NFO-Dateien und zugehörige Bilder.

## Version 0.2.0

- vorhandene NFO-Dateien erkennen und UTF-8-sicher anzeigen
- NFO-Dateien aus den Formularwerten neu erstellen oder aktualisieren
- automatische Sicherung jeder bestehenden NFO vor dem Schreiben
- Poster, Fanart, Banner und Thumbnail erkennen
- Bilder über einen lokalen Quelldateipfad austauschen
- automatische Sicherung ersetzter Bilder
- unverändert sichere Entwürfe und Vorher-/Nachher-Vergleiche
- MediaHub-Datenbankänderungen weiterhin nur über `metadata.update`

## Sicherungen

Sicherungen liegen unter `plugin_data/metadata_editor/backups`. Alle JSON-, XML- und Markdown-Dateien werden UTF-8-kodiert verarbeitet. Nicht als UTF-8 lesbare NFO-Dateien werden nicht automatisch überschrieben.

## Build

```powershell
python validate_plugins.py
python build_plugins.py metadata_editor --clean
```

Ausgabe: `release/MediaHub_MetadataEditor_v0.2.0.mhplugin`
