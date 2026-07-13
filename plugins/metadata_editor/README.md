# MediaHub Metadata Editor 0.1.0

Der Metadata Editor ist das dritte optionale MediaHub-Plugin. Er lädt die
MediaHub-Bibliothek über die freigegebene Plugin-API und bietet eine lokale
Oberfläche zum Suchen, Anzeigen, Vergleichen und Vorbereiten von Metadaten.

## Version 0.1.0

- Bibliotheksliste mit Suche
- Bearbeitung von Titel, Beschreibung, Jahr, Staffel und Episode
- Felder für Serie, Kanal, Playlist und Veröffentlichungsdatum
- Vergleich zwischen alten und neuen Werten
- lokale, absturzsicher geschriebene Metadaten-Entwürfe
- sicherer Entwurfsmodus, solange MediaHub `metadata.update` noch nicht anbietet
- gemeinsame lokale WebRuntime mit WebRemote und Mobile Dashboard
- feste Adresse `/metadata-editor`

## Sicherheit

Das Plugin überschreibt in Version 0.1.0 keine Dateien direkt. Eine endgültige
Änderung wird ausschließlich über die öffentliche MediaHub-Aktion
`metadata.update` angefordert. Ist diese Aktion nicht verfügbar, bleibt der
Button gesperrt und Änderungen können als Entwurf gespeichert werden.

## Installation und Build

```powershell
python validate_plugins.py
python build_plugins.py metadata_editor --clean
```

Das Paket wird als `release/MediaHub_MetadataEditor_v0.1.0.mhplugin` erstellt.
