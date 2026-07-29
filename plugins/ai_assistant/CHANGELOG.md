# Changelog

## 2.1.9 – Visual Intelligence Integration

- Vollständige Integrationsprüfung für alle Visual-Intelligence-Bausteine.
- Smart Frames, Visual Fingerprint, Scene Signature, OCR-/Logo-Fusion, anonyme Motive und Intro-/Outro-Erkennung werden gemeinsam validiert.
- Datenschutzstatus, nicht-biometrische Verarbeitung und Logo-Heuristik werden automatisch geprüft.
- Inkonsistente Frameanzahlen oder fehlende Pflichtbereiche werden klar gemeldet.
- Der Online-Provider bleibt standardmäßig deaktiviert und freigabepflichtig.
- Diese Version ist der Abschluss des lokalen v2.1.x-Visual-Intelligence-Blocks.

## 2.1.8 – Online Visual Provider

- Neue konfigurierbare Provider-Schnittstelle für visuelle Online-Suchen.
- Der Provider ist standardmäßig deaktiviert.
- Jede Übertragung erfordert eine ausdrückliche Benutzerfreigabe.
- Es werden maximal ausgewählte Einzelbilder übertragen, niemals komplette Videos oder Audiospuren.
- Frame-Export erfolgt nur temporär und in reduzierter Auflösung.
- Endpoint, API-Token, Timeout und maximale Frameanzahl sind konfigurierbar.
- Ohne Freigabe bleibt die gesamte Visual-Intelligence-Pipeline lokal.

## 2.1.7 – Visual Knowledge

- Bestätigte visuelle Signaturen können dauerhaft mit einer Medienidentität verknüpft werden.
- Visual Fingerprint, Scene Signature, OCR-/Logo-Hinweise, Intro-/Outro-Daten und anonyme Zentralmotive werden gemeinsam gespeichert.
- Automatische visuelle Funde bleiben Vorschläge und werden ohne Benutzerbestätigung nicht persistiert.
- Exakte visuelle Signaturen können lokal nachgeschlagen werden.
- Ein Export-Snapshot bereitet die Übergabe an Knowledge Graph und Listen-&-Export-Plugin vor.
- Alle Daten bleiben lokal.

## 2.1.6 – Intro-/Outro-Erkennung

- Framepositionen, Szenenrhythmus, OCR-/Logo-Kandidaten und anonyme Zentralmotive werden gemeinsam ausgewertet.
- Wahrscheinliche Vorspann- und Abspannbereiche erhalten getrennte Vertrauenswerte.
- Titelkarten und Studiotexte verstärken die jeweiligen Bereichskandidaten.
- Die Ausgabe bleibt bewusst heuristisch und kennzeichnet ihre Grenzen.
- Alle Analysen bleiben lokal; es erfolgt keine externe Übertragung.

## 2.1.5 – Character Recognition Preparation

- Der Frame-Agent erzeugt zusätzlich einen lokalen Hash des zentralen Bildbereichs.
- Wiederkehrende Zentralmotive werden anonym als `subject-001`, `subject-002` usw. gruppiert.
- Häufigkeit, Positionen und ein lokaler Wichtigkeitswert werden gespeichert.
- Es findet ausdrücklich keine Gesichtserkennung, biometrische Identifikation oder Namenszuordnung statt.
- Die bestätigte OCR-Mindestqualitätskorrektur aus v2.1.4 ist enthalten.
- Alle Daten bleiben lokal und werden nicht extern übertragen.

## 2.1.4 – OCR + Logo Fusion

- OCR-Text wird gemeinsam mit Framequalität, Schärfe, Kontrast und Zeitposition bewertet.
- Gute Intro- und Abspanntexte werden als Titelkarten-Kandidaten priorisiert.
- Kurze, saubere und überwiegend großgeschriebene Texte können als Logo-Kandidaten markiert werden.
- Logo-Kandidaten sind ausdrücklich OCR-/Layout-Heuristiken, noch keine objektbasierte Logoerkennung.
- OCR-Zeichensalat bleibt als verworfener Diagnosetreffer sichtbar.
- Doppelte Textkandidaten werden normalisiert zusammengeführt.
- Alle Auswertungen bleiben lokal.

## 2.1.3 – Scene Signature

- Szenenwechsel werden in normalisierte Segmente umgewandelt.
- Szenenlängen, Schnittrate und Rhythmus werden laufzeitunabhängig gespeichert.
- Intro-, Inhalts- und Outro-Segmente werden getrennt ausgewertet.
- Ausgewählte visuelle Frame-Hashes werden den nächstliegenden Szenen zugeordnet.
- Szenenstrukturen können tolerant miteinander verglichen werden.
- Der korrigierte Duplikatfilter aus v2.1.2 ist vollständig enthalten.
- Alle Daten bleiben lokal; es erfolgt keine externe Übertragung.

## 2.1.2 – Visual Fingerprint

- Jeder ausgewählte Frame erhält einen lokalen Average-Hash und Difference-Hash.
- Mehrere gute Frames werden zu einem toleranten visuellen Fingerprint zusammengeführt.
- Der Vergleich berücksichtigt passende Frame-Hashes und ein normalisiertes Bildprofil.
- Leichte Neukodierung, Skalierung und kleine Helligkeitsabweichungen können toleriert werden.
- Exakte `visual_signature` und toleranter `visual_fingerprint` bleiben getrennt.
- Es werden weiterhin keine Frames oder Videos extern übertragen.

## 2.1.1 – Smart Frame Selection

- Zeitliche Stichproben konzentrieren sich gezielt auf Vorspann, Handlung und Abspann.
- Bis zu 20 kleine lokale Graustufenframes werden effizient bewertet.
- Neue Messwerte für Schärfe, Bildinhalt, Schwarzbild- und Weißbildanteil.
- Unscharfe, dunkle, überbelichtete und nahezu identische Frames werden verworfen.
- Die visuelle Signatur nutzt nur die besten unterschiedlichen Kandidaten.
- Es findet weiterhin keine externe Bild- oder Videoübertragung statt.

## 2.1.0 – Visual Intelligence Core

- Bewertet Frame-Stichproben nach Helligkeit, Kontrast, Bildinhalt, OCR-Hinweisen und Position im Video.
- Filtert dunkle und visuell ähnliche Frames aus.
- Erzeugt eine lokale visuelle Signatur aus den besten Kandidaten.
- Speichert Datenschutzstatus; keine Bilder oder Ausschnitte werden automatisch extern übertragen.
- Bereitet eine spätere, ausdrücklich aktivierbare Online-Bild-/Szenensuche vor.

## 2.0.1 – Fingerprint Learning Fix

- Fingerprints werden beim bestätigten Lernen nicht mehr nur an einem festen Analysepfad gesucht.
- Cache-, Orchestrator- und verschachtelte Analyseergebnisse werden rekursiv durchsucht.
- Die Lernantwort zeigt mit `fingerprint_detected` und `fingerprint_source`, ob und wo der Fingerprint gefunden wurde.
- Der bestätigte Fingerprint wird weiterhin mit Identität, Vertrauen, Quelle und Quelldatei gespeichert.

## 2.0.0

- Benutzerbestätigte Identitäten werden dauerhaft gelernt.
- Korrekturen erzeugen bestätigte Aliasregeln mit Herkunft und Vertrauen.
- Fingerprints werden mit der bestätigten Wissensidentität verknüpft.
- Widersprüchliche Aliasregeln werden als Konflikte gespeichert.
- Lernwissen kann formatneutral für Listen-, PDF-, HTML- und Excel-Exporte ausgegeben werden.
- Filme, Serien, Episoden, Hörbücher und Bücher werden unterstützt.

# MediaHub KI-Assistent v1.9.2

- Einheitlicher QueryPlan als einzige Quelle für Provider-Suchvarianten.
- Provider führen ausschließlich freigegebene Varianten samt Qualitäts- und Herkunftsmetadaten aus.
- Verworfene Varianten bleiben diagnostisch erhalten, erreichen aber keinen Provider.
- Veraltete Online-Ergebnisse werden bei Cache-Neubewertung zuverlässig entfernt.
- Regressionstests für die `pso aqua`-/`aqua`-Cache-Umgehung.

# MediaHub KI-Assistent v1.9.1

- Qualitätsprüfung für jede Suchvariante vor Online-Abfragen.
- OCR-Zeichensalat wird verworfen und separat diagnostiziert.
- Lokale Wissens- und Aliasvarianten bleiben bevorzugt zugelassen.
- Erklärbare Qualitätswerte und Ablehnungsgründe im Query-Reasoning.
- Regressionstests für `pso aqua` und OCR-Rauschen.

# MediaHub KI-Assistent v1.9.0

- Knowledge Graph Intelligence mit erklärbaren, nicht automatisch gespeicherten Ableitungen.
- Erkennt Franchise-/Universumscluster aus bestehenden Beziehungen.
- Leitet Spin-off-Beziehungen aus Backdoor-Pilot- und Starts-in-Episode-Ketten ab.
- Erkennt Lücken in gespeicherten Reihenfolgen.
- Export-Snapshots enthalten nun Graph-Intelligence-Vorschläge.

# Changelog

## 1.8.1 – Evidence Gate Fix

- Schwache Einzelwort- und mehrdeutige Online-Treffer werden nicht mehr als Identitätsbestätigung gezählt.
- Nur `probable_match` und `strong_match` dürfen Online-Evidenz positiv bestätigen.
- Mindestscore, kombinierte Belege und blockierende Ranking-Strafwerte werden geprüft.
- Supervisor trennt Roh-Onlinekonfidenz von tatsächlich bestätigter Onlinekonfidenz.
- Regressionstest für `pso aqua2 ts` gegen den Wikipedia-Treffer `Aqua` ergänzt.

## 1.8.0 – Knowledge Graph Core

- Graph-Navigation mit Nachbarschafts- und Tiefensuche ergänzt.
- Franchise-, Universums-, Spin-off-, Prequel-, Sequel- und Crossover-Auflösung erweitert.
- Backdoor-Piloten, Starts-in-Episode, erste Auftritte, Episoden- und Staffelbeziehungen vorbereitet.
- Quellen- und Vertrauensinformationen an Entitäten und Beziehungen unterstützt.
- Export-Snapshot für Listen & Export mit HTML-, PDF- und Excel-Zielstruktur ergänzt.
- Filme, Serien, Staffeln, Episoden, Specials, Bücher und Hörbücher als Graph-Entitäten vorbereitet.

## 1.6.1

- Online-Agent verwendet den vollständigen Query aus dem Quellenplan.
- Alle Suchvarianten werden tatsächlich gegen jeden Provider ausgeführt.
- Providerergebnisse enthalten die ausgeführten Abfragen unter `queries`.
- Treffer erhalten Suchvariante, Variantengewicht, Herkunft und Begründung.
- Doppelte Treffer werden variantenübergreifend zusammengeführt.
- SourceManager.execute() vollständig und eindeutig ersetzt.
- Interne Strukturprüfung für SourceManager und OnlineAgent ergänzt.

## 1.6.0

- Gewichteten Suchvarianten-Reasoner ergänzt.
- Technische Dateinamenzusätze und OCR-Rauschen gefiltert.
- Provider mit mehreren Titelvarianten abgefragt.
- Treffer mit verwendeter Suchvariante und Gewicht versehen.
- Doppelte Providertreffer zusammengeführt.

## 1.5.0

- Unbekannte Medientypen für die Online-Recherche freigegeben.
- Provider anhand vorhandener Titel- und Identitätshinweise ausgewählt.
- Medientypübergreifende Suche ergänzt.
- Quellen- und Entscheidungslogik bei alten Cachetreffern neu berechnet.
- Teure technische und In-Video-Analyse bleibt dabei im Cache.
- Auswahlmodus und Auswahlbegründung im Quellenplan ergänzt.

## 1.4.0

- Zentrale Provider-Registry eingeführt.
- Parallele Providerausführung ergänzt.
- Lokalen Providercache und Diagnosen ergänzt.
- Kompatibilität mit OnlineAgent und Ranking erhalten.

## 1.3.3

- Wissens-Engine vollständig gegen alle Aufrufe aus `plugin.py` abgeglichen.
- `stats()`, `all_items()` und `seed_demo_data()` ergänzt.
- `ensure_schema()`, `initialize()`, `search()` und `status()` vereinheitlicht.
- Doppelten `knowledge_engine`-Statusschlüssel beseitigt.
- Separaten Statistikblock `knowledge_engine_stats` ergänzt.
- Idempotente Beispieldaten mit chronologischer, Veröffentlichungs- und
  Anschau-Reihenfolge ergänzt.
- Wissensgraph wird atomar geschrieben.
- Bestehende `knowledge.sqlite3` bleibt unverändert erhalten.

## 1.3.2

- Fehlende `KnowledgeEngine.ensure_schema()` ergänzt.
- Kompatiblen `initialize()`-Alias ergänzt.
- Wissensgraph wird beim Start sicher initialisiert.
- Pluginstart nach Einführung der Wissens-Engine repariert.

## 1.3.1

- Windows-Fehler 183 beim Start der Wissens-Engine behoben.
- Vorhandene `knowledge.sqlite3` wird korrekt als Datei erkannt.
- Neuer Wissensgraph verwendet den separaten Ordner `knowledge_graph`.
- Bestehende SQLite-Wissensdaten bleiben vollständig erhalten.

## 1.3.0

- Lokale Wissens-Engine mit persistentem Wissensgraph ergänzt.
- Medienobjekte, Aliase und externe IDs speicherbar gemacht.
- Franchise-, Universums-, Spin-off-, Prequel-, Sequel- und Crossover-Beziehungen ergänzt.
- Remake-, Reboot- und alternative Zeitlinien unterstützt.
- Chronologische Reihenfolge getrennt von Veröffentlichungsreihenfolge gespeichert.
- Eigene empfohlene Anschau-Reihenfolge ergänzt.
- Benutzerdefinierte Reihenfolgen vorbereitet.
- Wissens-Engine-Status in den Plugin-Systemstatus aufgenommen.

## 1.2.1

- Zentralen Agent-Manager ergänzt.
- Agentenregister mit Fähigkeiten, Werkzeugen und Kategorien eingeführt.
- Vorhandene lokale Analyseagenten als implementiert registriert.
- Ausstehende Wissens-, Online- und Supervisor-Agenten sichtbar gemacht.
- Vorbereitung für parallele Agentenausführung ergänzt.
- Agentenstatus in den Plugin-Systemstatus aufgenommen.

## 1.2.0

- Zentralen lokalen KI-Orchestrator ergänzt.
- KI-Anfragen werden in nachvollziehbare Teilschritte zerlegt.
- Fähigkeiten und benötigte Werkzeuge werden pro Schritt geprüft.
- Blockierte und noch nicht ausführbare Schritte werden begründet.
- Bestehende Medienanalyse läuft als erster produktiver Orchestrator-Schritt.
- Remote- und Cloud-Ausführung bleiben ausdrücklich deaktiviert.

## 1.1.4

- AI-Node-Version wird korrekt vom Root-Endpunkt gelesen.
- Antwortzeit der Statusabfragen ergänzt.
- Pluginzahlen des AI-Nodes sichtbar gemacht.
- CPU-, RAM-, Datenträger- und Temperaturstatus ergänzt.
- Capability-IDs durch verständliche deutsche Bezeichnungen ersetzt.

## 1.1.4

- AI-Node-Version wird korrekt vom Root-Endpunkt gelesen.
- Antwortzeit der Statusabfragen ergänzt.
- Pluginzahlen des AI-Nodes sichtbar gemacht.
- CPU-, RAM-, Datenträger- und Temperaturstatus ergänzt.
- Capability-IDs durch verständliche deutsche Bezeichnungen ersetzt.

## 1.1.3

- AI-Node-Verbindungsdaten werden automatisch aus MediaHub übernommen.
- `config/settings.json` ist die verbindliche Quelle.
- Host, API-Port und API-Token werden unterstützt.
- Backend-Konfiguration wird ohne Plugin-Neustart aktualisiert.
- Lokale KI bleibt Standard und Fallback.

## 1.1.2

- Reiter „Backends & Fähigkeiten“ ergänzt.
- Backend-Erreichbarkeit sichtbar gemacht.
- Fähigkeiten und fehlende Werkzeuge verständlich dargestellt.
- Task-Zähler und letzter Auftrag ergänzt.

## 1.1.1

- Zentrale Capability-Verwaltung ergänzt.
- KI-Funktionen werden den benötigten Werkzeugen zugeordnet.
- Fehlende Pflicht- und optionale Werkzeuge werden getrennt ausgewiesen.
- MKVToolNix wird in MKVMerge und MKVPropEdit aufgelöst.
- Grundlage für gemeinsame Tool-Verwaltung mit weiteren Plugins und dem AI-Node geschaffen.

# Changelog

## 1.0.0

- Erklärbare KI-Entscheidung mit Gründen, Einschränkungen und Widerspruchserklärung.
- Lokale SQLite-Fingerprint-Referenzdatenbank ergänzt.
- Bestätigte Fingerprints können später eindeutige Medienidentitäten liefern.
- Stabile Integrations-API für Metadata Editor und Universal Renamer ergänzt.
- Sicherheitsvertrag festgeschrieben: Vorschau und Bestätigung vor jeder Änderung.
- Finale Supervisor-/Decision-Engine-Zustände vereinheitlicht.

## 0.9.5

- Neue Decision Engine führt Dateiname, Online-Treffer, OCR, Untertitel, Fingerprint und technische Hinweise zusammen.
- Jede Quelle erhält getrennte Sicherheit, Gewichtung und Begründung.
- Unabhängige Bestätigungen werden gezählt und zu einer nachvollziehbaren Gesamtsicherheit kombiniert.
- Titelwidersprüche zwischen Dateiname und Online-/Inhaltsbeweisen werden ausdrücklich gemeldet.
- Klare Entscheidungsstufen ergänzt: bestätigt, wahrscheinlich, Prüfung empfohlen, unzureichend oder Widerspruch.
- Supervisor übernimmt jetzt den tatsächlichen Abschlusszustand der In-Video-Agenten statt sie nach erfolgreicher Analyse weiter als ausstehend anzuzeigen.
- Automatische Änderungen bleiben auch bei bestätigter Identität gesperrt; Vorschau und Benutzerbestätigung bleiben Pflicht.

## 0.9.0

- Begrenzte echte In-Video-Analyse statt bloßer Ausführungsplanung.
- FrameAgent liest reale Helligkeits-, Kontrast- und Sättigungswerte aus Stichproben.
- SubtitleAgent extrahiert Text, Schlüsselbegriffe und mögliche Eigennamen aus der ersten Untertitelspur.
- AudioAgent misst Lautheit, Dynamik und mögliches Clipping in einer begrenzten Audiostichprobe.
- OCRAgent analysiert ausgewählte Frames mit dem zentral installierten Tesseract.
- FingerprintAgent erzeugt einen reproduzierbaren Fingerprint aus normalisierten Videoframes.
- SceneAgent erkennt Szenenwechsel in einem begrenzten Analysefenster.
- Quality Engine v2 kombiniert technische Daten mit gemessenen Bild- und Audiowerten.
- Analyseausgabe zeigt Status und Zahl der tatsächlich ausgeführten In-Video-Agenten.
- Tiefenanalyse bleibt ressourcenschonend begrenzt und verändert keine Mediendateien.

## 0.8.0

- In-Video-Agent von einem Platzhalter zu einer ausführbaren Orchestrierungsbasis erweitert.
- Frame-, OCR-, Untertitel-, Audio-, Fingerprint-, Szenen- und Quality-Agent als getrennte Stufen definiert.
- Technische Bildqualitätsbewertung ergänzt.
- Technische Audioqualitätsbewertung einschließlich Codec, Bitrate, Kanälen und Abtastrate ergänzt.
- Getrennte Bild-, Ton- und Gesamtbewertung mit nachvollziehbaren Gründen eingeführt.
- Qualitätsstatus für Bibliotheksmarkierungen vorbereitet.
- Persönliche Referenzprofile für akzeptable Mindestqualität ergänzt.
- Qualitätsbewertung führt nie automatisch Änderungen an Medien aus.

## 0.7.0

- Echter ProviderManager mit TMDb, TheTVDB und Wikipedia.
- Einheitliches Online-Trefferformat eingeführt.
- Gewichtetes Mehrquellen-Ranking auf Schema-Version 2 erweitert.
- Staffel, Folge und Laufzeit in die Bewertung aufgenommen.
- Wikipedia als sofort nutzbare schlüssellose Testquelle aktiviert.
- Internet-Berechtigung für Online-Provider ergänzt.
- In-Video-Eskalation unverändert beibehalten.

## 0.6.0

- Kostenmodell für alle Erkennungsagenten ergänzt.
- Supervisor plant Agenten nach Sicherheit, Nutzen und Aufwand.
- Aktivierte und konfigurierte Online-Provider werden automatisch ausgeführt.
- Provider werden nach Medientyp und Priorität ausgewählt.
- Treffer verschiedener Quellen werden vereinheitlicht und gemeinsam bewertet.
- In-Video-Erkennung bleibt als verpflichtende Eskalationsstufe für unklare Fälle vorgesehen.


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
