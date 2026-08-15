# Changelog

## 0.4.1

- Mehrere lokale Quellordner können dauerhaft als Medienquellen gespeichert werden.
- Gespeicherte Quellordner können gemeinsam erneut und rekursiv eingelesen werden.
- Beim erneuten Scan werden Dateien als `new`, `changed` oder `unchanged` erkannt.
- Für die Änderungsverfolgung werden nur leichte Dateisignaturen aus Pfad, Größe und Änderungszeit verwendet.
- Es wird keine dauerhafte vollständige Medien- oder Dateiliste geführt.
- Die bisherige Einzelordner-Konfiguration wird in die neue Quellenverwaltung übernommen.
- Metadaten-Entwürfe sind jetzt sitzungsbezogen und werden nicht mehr dauerhaft in `drafts.json` gespeichert.
- Sitzungsentwürfe können vollständig verworfen werden.
- Für tatsächliche Änderungen ist eine dauerhafte Recovery-Grundlage mit Vorher-/Nachher-Zustand vorbereitet.
- Recovery-Daten werden getrennt von temporären Bearbeitungsentwürfen gespeichert.
- Metadata Write bleibt weiterhin gesperrt; Schreibvorgänge erfolgen noch nicht automatisch.
- Regressionstests für Quellenverwaltung, Neu-Scan, Sitzungsentwürfe und Recovery ergänzt.
## 0.3.8
- Kleine **Poster-Vorschau** direkt neben den Metadaten.
- Automatische Suche nach `poster.jpg/png` und `folder.jpg/png`.
- Explizite Poster-/Cover-Pfade aus MediaHub-Einträgen werden berücksichtigt.
- Nach **Poster ersetzen** wird die Vorschau sofort aktualisiert.
- Fehlende oder unlesbare Poster werden eindeutig angezeigt.

## 0.3.7
- Neuer Button **Ordner laden…** in der nativen Metadata-Editor-Oberfläche.
- Beliebige lokale Medienordner können rekursiv eingelesen werden.
- Lokale Dateien erscheinen in der Kategorie **Lokaler Ordner**.
- Vorhandene Sidecar-NFOs werden beim Einlesen berücksichtigt.
- MediaHub-/YouTube-Bibliothek bleibt parallel erhalten.
- Der zuletzt gewählte lokale Ordner wird lokal gespeichert.

## v0.3.6

- Bildbereich auf der allgemeinen Web-/Mobilansicht ergänzt.
- Poster, Fanart und Staffel-/Playlistbild mit Vorschau, Dateiname, Auflösung und Größe.
- Lokale Bildvorschauen werden sicher als eingebettete Daten ausgeliefert.
- Schnellzugriff für Medienordner, Video, NFO, Bilder, MediaInfo und Eigenschaften ergänzt.
- Responsive Darstellung für Handy und Tablet verbessert.

## v0.3.5

- Web-Umschalter „Allgemein | Erweiterter Editor“ ergänzt.
- Filter „Vorhandene Videos“ ergänzt.
- Weboberfläche für WebRemote und Mobile Dashboard veröffentlicht.

## v0.3.2

- Metadata Editor öffnet sich als eigenes Desktop-Fenster.
- Große Editoroberfläche ist frei vergrößerbar und maximierbar.
- Reine Weboberflächen werden nicht im MediaHub-Bereich „Plugin-Oberflächen“ geführt.

## v0.3.1

- Echte native Qt-Oberfläche direkt im MediaHub-Hauptfenster.
- Dreigeteilter Medienbrowser mit Kategorien, Medienliste und Metadatenformular.
- Entwürfe, NFO-Speicherung und Poster-Austausch aus der In-Program-GUI.
- Weboberfläche bleibt als zusätzliche lokale Oberfläche erhalten.
- UTF-8-Kodierung geprüft.

## 0.3.0

- vollständige dreigeteilte Medienbrowser-GUI ergänzt
- Navigation für Medien, Kanäle, Serien, Playlists und Entwürfe ergänzt
- Suche und Gruppenfilter ergänzt
- Live-Vergleich während der Eingabe ergänzt
- Entwürfe können geladen und gelöscht werden
- responsive Darstellung für kleinere Bildschirme ergänzt
- UTF-8-Ausgabe und automatische Sicherungen beibehalten

## 0.2.0

- NFO-Dateien erkennen, erstellen und UTF-8-sicher aktualisieren
- automatische NFO-Sicherungen
- Poster, Fanart, Banner und Thumbnail erkennen und ersetzen
- automatische Bildsicherungen

## 0.1.0

- erstes Plugin-Grundgerüst
- Bibliothek laden und Metadatenentwürfe speichern
