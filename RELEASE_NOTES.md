# MediaHub Plugins v0.5.11 – vollständiges Release

## MediaHub KI-Assistent v7.0.7

- Online-Metadaten-Erkennung für Serien und Episoden erweitert.
- TheTVDB- und TMDb-Provider ausgebaut und in die gemeinsame Provider-Auswertung integriert.
- Episodentitel können aus Online-Quellen erkannt und in KI-Reviews übernommen werden.
- Seriennamen werden bei unbrauchbaren oder technisch geprägten Dateinamen zuverlässiger bereinigt.
- Beschreibung sowie Veröffentlichungs-/Ausstrahlungsdatum können aus Online-Evidenz in die Metadaten-Vorschau übernommen werden.
- Neue Metadata-Review-Capability für die Zusammenarbeit mit dem Metadata Editor.
- Rename-Review- und Batch-Rename-Review-Schnittstellen für den Smart Renamer erweitert.
- Provider-Einstellungen werden dauerhaft gespeichert.
- Aktiviert-/Deaktiviert-Zustand der Quellen bleibt nach Plugin-Updates erhalten.
- Provider-Zugangsdaten werden getrennt vom Plugin dauerhaft und unter Windows per DPAPI geschützt gespeichert.
- Zugangsdaten bleiben bei Plugin-Neuinstallation bzw. Plugin-Update erhalten.
- Provider-Verbindungstest verwendet den aktuellen gespeicherten Formular- und Aktivierungszustand.
- Umfangreiche neue Regressionstests für Provider, Episodenerkennung, Metadata Review und Rename Review ergänzt.

## MediaHub Audio Metadata Editor v0.0.1

- Neues eigenst?ndiges MediaHub-Plugin f?r Audio-Metadaten und H?rb?cher.
- Ersetzt die bisherige geplante MediaHub H?rbuchverwaltung als gemeinsame Audio-Metadaten-L?sung.
- Audio und H?rb?cher werden innerhalb desselben Plugins verwaltet.
- Gemeinsamer Audio-Metadata-Contract f?r Lesen, Erkennen, Vergleichen, Schreibplanung und sp?tere Schreibvorg?nge vorbereitet.
- Gemeinsame MediaHub-Metadata-Core-Infrastruktur f?r Audio- und Video-Metadaten angebunden.
- Unterst?tzte Audioformate und sichere Schreibregeln zentral vorbereitet.
- H?rbuchdateien wie M4B werden bereits als eigener Medientyp erkannt.
- Tool-Anbindung f?r FFmpeg, FFprobe, MediaInfo, Chromaprint/fpcalc und Mp3tag vorbereitet.
- Drittanbieter-, Lizenz-, Installations- und Tool-Dokumentation ist Bestandteil des Plugins.
- Tats?chliches Schreiben von Audio-Tags bleibt in v0.0.1 noch deaktiviert.
- ?nderungen bleiben best?tigungspflichtig; Backup und Pr?fung nach sp?teren Schreibvorg?ngen sind verbindlich vorgesehen.

## MediaHub Metadata Editor v0.4.2

- Lokale Ordner können direkt ausgewählt und als Medienquelle eingelesen werden.
- Mehrere lokale Quellordner können dauerhaft als Quellen gespeichert und gemeinsam erneut eingelesen werden.
- Beim erneuten Einlesen werden Dateien als `new`, `changed` oder `unchanged` erkannt.
- Die Änderungsverfolgung speichert nur leichte Dateisignaturen aus Pfad, Größe und Änderungszeit; es wird keine dauerhafte vollständige Medienliste geführt.
- Die bisherige Einzelordner-Konfiguration wird in die neue Quellenverwaltung übernommen.
- MediaHub-/YouTube-Bibliothek und lokale Ordner stehen als getrennte Quellen zur Verfügung.
- Vorhandene Metadaten aus Datei und NFO werden separat angezeigt.
- KI-Metadaten-Vorschau mit Alt-/Neu-Vergleich integriert.
- KI-Vorschläge können die Bearbeitungsfelder im Entwurf vorausfüllen.
- Serienname, Staffel, Episode und Episodentitel werden aus dem KI-Assistenten übernommen.
- Beschreibung sowie Veröffentlichungs-/Ausstrahlungsdatum können in den Metadaten-Entwurf übernommen werden.
- Poster-Vorschau für lokale bzw. online ermittelte Bilder ergänzt.
- Grunddaten-, Serien- und Quellenbereiche neu strukturiert.
- Staffel und Episode werden gemeinsam und übersichtlich dargestellt.
- Beschreibung im Hauptfenster auf eine kompakte Vorschau reduziert und kann über einen separaten Dialog vollständig bearbeitet werden.
- Metadaten-Entwürfe sind jetzt sitzungsbezogen und werden nicht mehr dauerhaft in `drafts.json` gespeichert.
- Sitzungsentwürfe können vollständig verworfen werden.
- Für tatsächliche Änderungen ist eine dauerhafte Recovery-Grundlage mit Vorher-/Nachher-Zustand vorbereitet.
- Recovery-Daten und temporäre Bearbeitungsentwürfe sind klar voneinander getrennt.
- Metadata Write bleibt weiterhin gesperrt; KI-Ergebnisse und Bearbeitungen bleiben aktuell Vorschläge/Entwürfe.
- Regressionstests für Quellenverwaltung, Neu-Scan, Sitzungsentwürfe, Recovery, Layout, Dialoge, Poster und KI-Metadaten ergänzt.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.
- Mobile Oberfläche für Handy und Tablet mit gemeinsamer lokaler MediaHub-Webbasis.

## MediaHub Smart Renamer v0.5.17

- Zusammenarbeit mit dem MediaHub KI-Assistenten deutlich erweitert.
- Rename-Review kann strukturierte KI-Empfehlungen auswerten.
- Batch-KI-Prüfung und Batch-Rename-Review erweitert.
- Episodentitel aus Online-/KI-Metadaten können in Umbenennungsvorschläge übernommen werden.
- Serien- und Episodenanker bei technisch geprägten Dateinamen verbessert.
- Auflösungs- und Technik-Tokens werden zuverlässiger von Staffel-/Episode-Angaben getrennt.
- KI- und Renamer-Ergebnisse können miteinander verglichen und Konflikte sichtbar gemacht werden.
- Metadaten-Capability-Anbindung für die gemeinsame Vorschau ergänzt.
- GUI-Anzeige für KI-Status, Review-Ergebnisse und Metadaten-Diagnose erweitert.
- Vorschläge bleiben bestätigungspflichtig; keine automatische Umbenennung ohne Benutzerfreigabe.
- Native und optionale externe Backends bleiben getrennt und über die bestehende Backend-Auswahl steuerbar.
- Umfangreiche neue Tests für KI-Review, Batch-Review, Metadaten-Anbindung und technische Dateinamenerkennung ergänzt.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.
- Lokale Desktop-/PC-Weboberfläche für MediaHub.

## MediaHub AI Test Provider v1.0.0

- Unveränderter AI-Node-/Raspberry-Pi-Plugin-Stand.
- Wird weiterhin als `.mhaiplugin` gemeinsam mit den MediaHub-Plugins gebaut und veröffentlicht.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.
