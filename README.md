# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub Metadata Editor 0.3.1**
- **MediaHub Mobile Dashboard 0.1.5**
- **MediaHub WebRemote 0.13.5**

# MediaHub Plugins – Metadata Editor v0.3.1

## Enthaltene Plugins

### MediaHub WebRemote v0.13.5

- Lokale Desktop-/PC-Weboberfläche für MediaHub.
- Gemeinsame lokale Webserver- und API-Basis beibehalten.

### MediaHub Mobile Dashboard v0.1.5

- Eigenständige mobile Oberfläche für Handy und Tablet.
- Gemeinsame einklappbare Sidebar für beide Geräteklassen.

### MediaHub Metadata Editor v0.3.1

- vollständige dreigeteilte Medienbrowser-GUI ergänzt
- Navigation für alle Medien, Kanäle, Serien, Playlists und Entwürfe ergänzt
- Suche und Gruppenfilter ergänzt
- vollständiges Metadatenformular mit Live-Vergleich ergänzt
- Entwürfe können gespeichert, geladen und gelöscht werden
- NFO- und Bildverwaltung mit automatischen Sicherungen beibehalten
- responsive Darstellung für kleinere Bildschirme ergänzt
- UTF-8-sichere Verarbeitung geprüft

## Build-Dateien

- `MediaHub_WebRemote_v0.13.5.mhplugin`
- `MediaHub_WebRemote_v0.13.5.mhplugin.sha256`
- `MediaHub_MobileDashboard_v0.1.5.mhplugin`
- `MediaHub_MobileDashboard_v0.1.5.mhplugin.sha256`
- `MediaHub_MetadataEditor_v0.3.1.mhplugin`
- `MediaHub_MetadataEditor_v0.3.1.mhplugin.sha256`

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
