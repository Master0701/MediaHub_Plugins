# Metadata Editor v0.3.0

Öffne den Metadata Editor über die Plugin-Verwaltung oder direkt unter `/metadata-editor`.

## Oberfläche

1. Links wählst du zwischen allen Medien, Kanälen, Serien, Playlists und Entwürfen.
2. In der mittleren Spalte suchst und filterst du die Bibliothek.
3. Rechts bearbeitest du Metadaten, NFO-Dateien und Bilder.

Der Live-Vergleich zeigt jede Änderung sofort an. Entwürfe verändern die MediaHub-Datenbank nicht. Vor Änderungen an NFO-Dateien oder Bildern wird automatisch eine Sicherung unter `plugin_data/metadata_editor/backups` erstellt.

Die Schaltfläche „MediaHub-Datenbank speichern“ ist nur aktiv, wenn das Hauptprogramm die kontrollierte Aktion `metadata.update` bereitstellt.


## Desktop-Fenster

Der Metadata Editor wird über „Plugin-Oberflächen“ als eigenes, frei vergrößerbares Desktop-Fenster geöffnet. WebRemote und Mobile Dashboard werden dort nicht angezeigt.


## Neu in v0.3.4

- Seiten „Allgemein“ und „Erweiterter Editor“
- Bildvorschauen für Poster, Fanart und Staffel/Playlist
- Schnellzugriff auf lokale Medien- und Metadatendateien
- Filter „Vorhandene Videos“ für lokal existierende Dateien
