# Changelog

## 0.4.5

- Plugin-spezifische Cache-Verwaltung für das Plugin Center ergänzt.
- Gesamter Analyse-Cache kann nach Sicherheitsabfrage gelöscht werden.
- Anzahl gespeicherter Analysen und Pfad der Cache-Datenbank werden angezeigt.
- Eigene `create_window()`-Schnittstelle für zuverlässiges Öffnen als Desktop-Fenster ergänzt.
- `create_widget()` bleibt als Abwärtskompatibilität erhalten.

## 0.4.2

- Medienerkennung aus Datei- und Ordnernamen deutlich erweitert.
- Erkennt Filme anhand von Titel und Jahr sowie Serien in SxxExx-, 2x03- und deutschen Staffel-/Folgenformaten.
- Erkennt Mehrfachfolgen, Specials und absolute Episodennummern.
- Erkennt zahlreiche Schnittfassungen wie Extended, Director's Cut, Uncut, Unrated, IMAX, Final Cut und Remastered.
- Nutzt bei schwachen Dateinamen aussagekräftige Elternordner als zusätzlichen Titelkandidaten.
- Liefert nachvollziehbare Gründe, mehrere Editionskandidaten und einen Hinweis für erforderliche externe Recherche.
- Desktop- und Webanzeige für Mehrfachfolgen, Fassungen und Erkennungsgründe erweitert.

## 0.4.1

- Web-Wissenssuche ohne Query-Parameter neu umgesetzt.
- Weboberfläche lädt den lokalen Wissensindex über einen festen Endpunkt.
- Suche und Alias-Suche werden direkt im Browser ausgeführt.
- Dadurch ist die Funktion unabhängig von der Query-Auswertung des RequestContext.
- Desktop-Wissenssuche bleibt unverändert serverseitig.

## 0.4.0

- Erste Knowledge Engine ergänzt.


## 0.4.3

- Zentrale Tool-Suche für MediaHub_Tools erweitert.
- Cache-Zeitpunkt, gezieltes Löschen und erzwungene Neuanalyse vorbereitet.
- Weitere Release-Gruppen und Störbegriffe entfernt.
- Gemeinsamer, nicht ausführender Änderungsplan für Renamer und Metadata Editor ergänzt.
- Architektur für zusätzliche Medientypen wie Hörbücher vorbereitet.
## 0.4.4

- Tool-Zuordnung für den globalen MediaHub-Tools-Status korrigiert.
- MediaInfo, MKVToolNix und Tesseract werden jetzt gemeinsam über `required_tools` registriert.
- Optionale Werkzeuge bleiben mit `required: false` optional, werden aber trotzdem als vom KI-Assistenten verwendet angezeigt.
- Verhindert, dass installierte Plugin-Werkzeuge im globalen Tools-Status wieder verschwinden.


## 0.5.0

- Modulares Quellen-Manager-Grundsystem ergänzt.
- TMDb, TheTVDB und IMDb als deaktivierte, konfigurierbare Provider vorbereitet.
- Eigene API-Quellen und eigene Webseiten-Scanner über `config/sources.json` vorgesehen.
- Supervisor-Agent ergänzt, der Online- und In-Video-Tiefenanalyse anhand der lokalen Sicherheit plant.
- In-Video-Agent als verbindliche Pipeline für OCR, Untertitel, Audio, Fingerprints und Schnittfassungserkennung angelegt.
- Bestehende technische Analyse, Cache-Funktion, Desktop-Fenster und Plugin-Einstellungen bleiben erhalten.
