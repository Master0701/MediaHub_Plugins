# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 7.0.7**
- **MediaHub Hörbuchverwaltung 0.0.0**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.4.0**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.5.17**
- **MediaHub WebRemote 0.13.7**
- **MediaHub AI Test Provider 1.0.0**

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

## MediaHub Metadata Editor v0.4.0

- Lokale Ordner können direkt ausgewählt und als Medienquelle eingelesen werden.
- MediaHub-/YouTube-Bibliothek und lokale Ordner stehen als getrennte Quellen zur Verfügung.
- Vorhandene Metadaten aus Datei und NFO werden separat angezeigt.
- KI-Metadaten-Vorschau mit Alt-/Neu-Vergleich integriert.
- KI-Vorschläge können die Bearbeitungsfelder im Entwurf vorausfüllen.
- Serienname, Staffel, Episode und Episodentitel werden aus dem KI-Assistenten übernommen.
- Beschreibung sowie Veröffentlichungs-/Ausstrahlungsdatum in den Metadaten-Entwurf integriert.
- Poster-Vorschau für lokale bzw. online ermittelte Bilder ergänzt.
- Grunddaten-, Serien- und Quellenbereiche neu strukturiert.
- Staffel und Episode werden gemeinsam und übersichtlich dargestellt.
- Beschreibung im Hauptfenster auf eine kompakte Vorschau reduziert.
- Vollständige Beschreibung kann über einen separaten Dialog gelesen und bearbeitet werden.
- Beschreibungsdialog bietet Zeilenumbruch, Scrollbalken, „Übernehmen“ und „Abbrechen“.
- Veröffentlichungs-/Ausstrahlungsdatum bleibt unabhängig von der Beschreibung sichtbar.
- Metadata Write bleibt weiterhin gesperrt; KI-Ergebnisse sind aktuell ausschließlich Vorschläge/Entwürfe.
- Umfangreiche Layout-, Dialog-, Ordner-, Poster- und KI-Metadaten-Tests ergänzt.

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

## Kompatibilität

- **MediaHub KI-Assistent 7.0.7** – mindestens MediaHub v1.0.17
- **MediaHub Hörbuchverwaltung 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.4.0** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.17** – mindestens MediaHub v1.0.18
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
