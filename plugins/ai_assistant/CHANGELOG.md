# Changelog

## 4.4.2 – German Parallel Continuity Declension Fix

- Ergänzt die deutschen Formen parallel, parallele, parallelen, paralleler und paralleles.
- Behebt die fehlende Erkennung von „in einem parallelen Universum“.
- Behält den normalisierten Knotenschlüssel 	imeline:parallel-universe.
- Produktive Änderungen wurden als echter Diff gegen den GitHub-Branch work/ai-assistant-v4.4 erstellt.
- Automatischer Import bleibt deaktiviert und alle Vorschläge bleiben bestätigungspflichtig.
## 4.4.1 – Continuity Node Key Normalization Fix

- Behebt Unterstriche in Canon- und Timeline-Knotenschlüsseln.
- `non_canon` wird jetzt zu `canon:non-canon`.
- `alternate_timeline` wird jetzt zu `timeline:alternate-timeline`.
- Entsprechend werden Parallel-, Prime- und Kelvin-Zeitlinien mit Bindestrichen gespeichert.
- Die Erkennungslogik und Bestätigungspflicht bleiben unverändert.

## 4.4.0 – Franchise Relation Intelligence Bundle

- Erkennt Sequel-, Prequel-, Midquel-, Spin-off- und Crossover-Beziehungen.
- Erkennt Reboot-, Soft-Reboot- und Remake-Beziehungen.
- Erkennt Director’s Cut, Extended Cut, Uncut, Remaster und Theatrical Cut.
- Erkennt Canon/Non-Canon sowie alternative, parallele, Prime- und Kelvin-Zeitlinien.
- Erzeugt bestätigungspflichtige Graph-Knoten und -Kanten ohne automatischen Import.
- Integriert die Ergebnisse in Graph-Vorschlag, Validator, Knowledge Graph, Reasoning Context und Scan-Ausgabe.
- Enthält eine umfangreiche Bundle-Testdatei mit realistischen und künstlichen Fällen.

## 4.3.5 – Graph Validation Version Regression Cleanup

- Entfernt die starre Prüfung auf exakt `VERSION = "4.3.2"`.
- Prüft stattdessen robust, dass eine gültige `4.3.x`-Version gesetzt ist.
- Produktivcode und Graph-Validierungslogik aus v4.3.4 bleiben unverändert.

## 4.3.4 – Graph Validation Test Import Path Fix

- Behebt `ModuleNotFoundError: No module named 'services'` im v4.3.3-Integrationstest.
- Fügt den Plugin-Ordner vor dem Service-Import zu `sys.path` hinzu.
- Produktivcode und vollständige Graph-Gruppenvalidierung aus v4.3.3 bleiben unverändert.

## 4.3.3 – Complete Graph Validation Group Integration

- Behebt dauerhaft den veralteten Variablennamen `character_graph`.
- Verwendet stattdessen das tatsächlich erzeugte Ergebnis `character_intelligence`.
- Ergänzt `relationship_proposal` in der gemeinsamen Graph-Validierung.
- Ergänzt `cast_resolution` in der gemeinsamen Graph-Validierung.
- Ergänzt `relationship_intelligence` in der gemeinsamen Graph-Validierung.
- Der Validator prüft jetzt alle zehn im Scan erzeugten Graph-Teilresultate.
- Ergänzt einen AST-basierten Integrations- und Laufzeit-Simulationstest.

## 4.3.2 – AST Graph Validation Order Test Fix

- Ersetzt den starren Teilstring-Test für `character_graph` und andere Variablen.
- Analysiert `plugin.py` jetzt über den Python-AST.
- Prüft, dass `graph_validation` genau einmal zugewiesen wird.
- Prüft, dass `graph_validation` nicht vor seiner Zuweisung gelesen wird.
- Prüft weiterhin den sicheren Dictionary-Filter für Graph-Gruppen.
- Produktivcode und Laufzeitlogik aus v4.3.1 bleiben unverändert.

## 4.3.1 – Graph Validation Initialization Order Fix

- Behebt `NameError: character_graph is not defined`.
- Verschiebt die Graph-Validierung hinter die Erzeugung aller benötigten Graph-Teilresultate.
- Sammelt nur vorhandene Dictionary-Graph-Gruppen für den Merge-Validator.
- Verhindert vergleichbare Initialisierungsfehler bei Event-, Relationship-, Universe- und Franchise-Ergebnissen.
- Ersetzt die zentrale `plugin.py` vollständig statt erneut einzelne Zeilen einzufügen.

## 4.3.0 – Knowledge Graph Merge & Validation Bundle

- Vereinigt Graph-Teilresultate aus Figuren, Beziehungen, Events, Universen und Franchises.
- Dedupliziert Knoten anhand `node_type + key`.
- Dedupliziert Kanten anhand Typ, Quelle und Ziel.
- Führt Quellen-IDs, Metadaten und Vertrauenswerte zusammen.
- Erkennt widersprüchliche Titel-, Jahres- und Typangaben.
- Erkennt Kanten mit fehlenden Quell- oder Zielknoten.
- Erzwingt Bestätigungspflicht und deaktiviert automatischen Import für alle zusammengeführten Ergebnisse.
- Bindet die Validierung in Reasoning Context und Scan-Ausgabe ein.
- Enthält eine umfangreiche Testdatei mit Einzel- und Kombinationstests.

## 4.2.3 – Franchise Strategy Regression Compatibility

- Ersetzt die vollständige Testdatei `test_franchise_collection_intelligence_v420.py`.
- Entfernt die starre Strategieprüfung auf exakt `franchise_collection_intelligence_v420`.
- Akzeptiert künftig kompatible Franchise-Strategien mit dem Präfix `franchise_collection_intelligence_v`.
- Produktivcode und Franchise-Logik aus v4.2.2 bleiben unverändert.

## 4.2.2 – Explicit Franchise Single-Installment Fix

- Behebt `installment_count = 0`, wenn doppelte Teile auf einen eindeutigen Teil reduziert werden.
- Ein ausdrücklich gesetzter Franchise-Name erlaubt jetzt auch eine Sammlung mit nur einem eindeutigen Teil.
- Deduplizierung bleibt aktiv: identische Titel, Jahre und Medientypen werden nur einmal gezählt.
- Ohne explizites Franchise und ohne sichere Beziehung bleibt die Schutzprüfung unverändert aktiv.
- Aktualisiert die Franchise-Strategie auf `franchise_collection_intelligence_v422`.

## 4.2.1 – Franchise Intelligence Bundle

- Unterstützt beliebig viele erkannte Franchise-Teile.
- Erzeugt getrennte Veröffentlichungs- und chronologische Reihenfolgen.
- Unterstützt Sequel-, Prequel-, Spin-off- und Crossover-Grundlagen.
- Dedupliziert identische Medien anhand Titel, Jahr und Medientyp.
- Behält gleichnamige Medien mit unterschiedlichen Jahren getrennt.
- Verarbeitet fehlende Jahreszahlen ohne Abbruch.
- Unterstützt mehrere Universumszugehörigkeiten eines Franchise.
- Erhält Rückwärtskompatibilität zur v4.2.0-Franchise-Struktur.
- Enthält eine umfangreiche Bundle-Testdatei mit realistischen und künstlichen Fällen.

## 4.2.0 – Franchise Collection Intelligence Phase 1

- Führt einen eigenen `franchise`-Knotentyp für zusammengehörige Medienreihen ein.
- Leitet das Franchise aus sicheren Vorgänger-/Nachfolgerbeziehungen ab.
- Verbindet aktuelle und vorherige Teile über `installment_of` mit dem Franchise.
- Übernimmt die Universumszugehörigkeit des aktuellen Teils als bestätigungspflichtigen Franchise-Vorschlag.
- Erzeugt für Aquaman eine Reihe mit `Aquaman (2018)` und `Aquaman: Lost Kingdom (2023)`.
- Bindet die Franchise-Sammlung in Graph-Vorschlag, Gesamtgraph, Reasoning Context und Scan-Ausgabe ein.
- Alle Ergebnisse bleiben Vorschläge und werden nicht automatisch importiert.

## 4.1.13 – Alias Fusion Strategy Test Compatibility

- Ersetzt die vollständige Testdatei `test_character_alias_identity_fusion_v418.py`.
- Entfernt die starre Strategieprüfung auf exakt `character_alias_identity_fusion_v418`.
- Akzeptiert künftig kompatible Strategien mit dem Präfix `character_alias_identity_fusion_v`.
- Produktivcode und Identity-Fusion-Logik aus v4.1.12 bleiben unverändert.

## 4.1.12 – Character Identity Fusion Data Cleanup

- Entfernt reale Schauspieler aus dem kanonischen Figuren-Identitätsgraphen.
- Verhindert falsche Character-Knoten wie `Jason Momoa` und `Amber Heard`.
- Blockiert reine Titel-Aliase wie `König`, `Königin`, `Dr.` und `Herrscher`.
- Bewahrt die Originalschreibweise kanonischer Figuren wie `David Kane`.
- Bevorzugt Character-Nodes aus der Besetzung gegenüber kleingeschriebenen Alias-Key-Fallbacks.
- Aktualisiert die Fusion-Strategie auf `character_alias_identity_fusion_v4112`.

## 4.1.11 – Stable Version Test Cleanup

- Entfernt die feste Prüfung auf exakt Version 4.1.9 aus dem stabilen Versionstest.
- Prüft nur noch gültige Versionssyntax und eine kompatible Version ab 4.1.0.
- Verhindert erneute Testfehler bei zukünftigen Patchversionswechseln.
- Produktivcode und Laufzeitlogik aus v4.1.10 bleiben unverändert.

## 4.1.10 – Event Initialization Test Indentation Fix

- Behebt den `IndentationError` in `test_event_initialization_order_v415.py`.
- Ersetzt die fehlerhaft eingefügte mehrzeilige Versionsprüfung vollständig.
- Prüft weiterhin eine gültige Plugin-Version ab 4.1.0.
- Produktivcode, Alias-Fusion, Event Intelligence und Relationship Engine bleiben unverändert.

## 4.1.9 – Stable Plugin Version Test Fix

- Entfernt die starre Versionsprüfung auf exakt 4.1.7 aus dem alten Event-Initialisierungstest.
- Prüft künftig eine gültige Plugin-Version ab 4.1.0.
- Verhindert erneute Testfehler bei jedem regulären Patchversionswechsel.
- Alias-, Identity-, Event- und Relationship-Laufzeitcode aus v4.1.8 bleiben unverändert.

## 4.1.8 – Character Alias & Identity Fusion Phase 2

- Führt Cast- und Relationship-Identitäten zu einem gemeinsamen Figurenmodell zusammen.
- Erstellt genau einen kanonischen Character-Knoten je erkannter Figur.
- Erhält Kurzformen und Decknamen als eigene `character_alias`-Knoten.
- Erzeugt eindeutige `alias_of`-Kanten zur kanonischen Figurenidentität.
- Löst Alias-Ketten transitiv bis zum endgültigen kanonischen Namen auf.
- Unterstützt unter anderem `Arthur/Aquaman → Arthur Curry`, `David/Black Manta → David Kane` und `Orm → Orm Marius`.
- Bindet die Identity Fusion in Graph-Vorschlag, Gesamtgraph, Reasoning Context und Scan-Ausgabe ein.
- Alle Ergebnisse bleiben bestätigungspflichtige Vorschläge.

## 4.1.7 – Event Initialization Regression Test Compatibility

- Aktualisiert den alten v4.1.5-Test auf die neue Identity-Map-Fusion aus v4.1.6.
- Prüft jetzt `RelationshipIdentityMapBuilder.build(...)` statt der entfernten direkten Event-Map-Zeile.
- Entfernt die starre Versionsprüfung auf exakt 4.1.5.
- Der Produktivcode und die Laufzeitlogik aus v4.1.6 bleiben unverändert.

## 4.1.6 – Relationship Identity Map Fusion

- Vereinigt sichere Event-Identitäten mit den kanonischen Figuren aus der Besetzung.
- Löst Kurzformen wie `Orm` zu `Orm Marius` auf.
- Bevorzugt verlässliche Cast-Identitäten gegenüber heuristischen Event-Zuordnungen.
- Filtert unsichere Alias-Einträge wie `titel`, `in`, `warner`, `stab` und `drehbuch`.
- Übergibt die bereinigte gemeinsame Identity-Map an die Character Relationship Engine.
- Legt die verwendete Map im Reasoning Context und Scan-Ergebnis offen.

## 4.1.5 – Event Intelligence Initialization Order Fix

- Behebt `UnboundLocalError: cannot access local variable 'event_intelligence'`.
- Führt die Event Intelligence vor der Character Relationship Engine aus.
- Übergibt die Event-Identity-Map erst nach erfolgreicher Initialisierung.
- Belässt Event-, Relationship- und Knowledge-Graph-Logik unverändert.
- Ergänzt Regressionstests für die korrekte Ausführungsreihenfolge.

## 4.1.4 – Relationship Strategy Test Compatibility

- Aktualisiert den veralteten v4.1.2-Regressionstest auf kompatible v4-Relationship-Strategien.
- Die produktive Relationship-Strategie bleibt unverändert auf `character_relationship_engine_v413`.
- Verhindert erneute Testfehler allein durch kompatible interne Strategie-Fortschreibungen.
- Der in v4.1.3 korrigierte Halbgeschwister-Parser bleibt unverändert.

## 4.1.3 – Relationship Subject Parser Rewrite

- Ersetzt die fehlerhafte Halbgeschwister-Subjektlogik vollständig.
- Erkennt normale Hauptsatzformen wie `Arthur befreit seinen Halbbruder Orm`.
- Erkennt Verb-Erstformen nach Nebensätzen wie `..., befreit Arthur seinen Halbbruder Orm`.
- Verhindert weiterhin Satzstarter wie `Um` als Figurenknoten.
- Wendet die Identity-Auflösung erst nach erfolgreicher Subjekterkennung an.
- Aktualisiert die Relationship-Strategie auf `character_relationship_engine_v413`.
- Entfernt die starre v411-Erwartung aus dem alten Regressionstest.

## 4.1.2 – Relationship Subject Boundary & Identity Resolution Fix

- Verhindert den falschen Figurenknoten `character:um` aus einleitenden Zweckklauseln.
- Bestimmt das Halbgeschwister-Subjekt aus dem letzten Hauptsatzteil vor der Verwandtschaftsangabe.
- Verwirft Satzstarter wie `Um`, `Als`, `Wenn`, `Nachdem` und `Unterdessen` als Figuren.
- Nutzt die bestehende Event-Identity-Map zur Kanonisierung von Relationship-Knoten.
- Führt dadurch `Arthur` mit `Arthur Curry` und `Orm` mit `Orm Marius` zusammen, sofern diese Identitäten bekannt sind.
- Relationship-Strategie auf `character_relationship_engine_v412` aktualisiert.

## 4.1.1 – German Relationship Word Order & Shared Subject Fix

- Erkennt deutsche Verb-Erstformen wie `heiratete Arthur Curry Mera`.
- Unterstützt weiterhin die Hauptsatzform `Arthur Curry heiratete Mera`.
- Übernimmt gemeinsame Satzsubjekte in Folgeklauseln wie `und bekam einen Sohn`.
- Erlaubt Verben zwischen Figur und Verwandtschaftsbezeichnung, etwa `Arthur befreit seinen Halbbruder Orm`.
- Begrenzt Verwandtschaftsnamen weiterhin vor Orts- und Präpositionsphrasen.
- Relationship-Strategie auf `character_relationship_engine_v411` aktualisiert.

## 4.1.0 – Character Relationship Engine Phase 1

- Führt eine eigene Engine für belastbare Figuren- und Familienbeziehungen ein.
- Erkennt Ehebeziehungen aus Formulierungen wie `Arthur Curry heiratete Mera`.
- Erkennt Eltern-/Kind-Beziehungen aus `bekam einen Sohn` und `bekam eine Tochter`.
- Erkennt Halbgeschwisterbeziehungen aus `seinen Halbbruder` und `seine Halbschwester`.
- Erkennt explizite Bruder-/Schwester-Beziehungen aus Appositionen wie `Kordax, Bruder von König Atlan`.
- Erzeugt gerichtete und reziproke Kanten, wo dies semantisch erforderlich ist.
- Bindet die neuen Beziehungen in Graph-Vorschlag, Gesamtgraph und Reasoning Context ein.
- Alle Ergebnisse bleiben bestätigungspflichtige Vorschläge.

## 4.0.11 – Escaped Wikipedia Cast Compatibility Fix

- Normalisiert escaped Wikipedia-JSON mit `\"` vor der Besetzungserkennung.
- Unterstützt sowohl `\\n` als auch mehrfach escaped `\\\\n` als Zeilentrenner.
- Stellt die Erkennung von Jason Momoa als erstem Infobox-Darsteller wieder her.
- Stellt Billing-Positionen für mehrere Besetzungseinträge wieder her.
- Stellt die `voices`-Kante für Rollen mit `(Stimme)` wieder her.
- Bewahrt den etablierten Strategienamen `character_cast_intelligence_v340` für Abwärtskompatibilität.
- Entfernt die exakte 4.0.8-Festlegung aus dem stabilen Versionstest.

## 4.0.10 – Wikipedia Cast Boundary Parser Fix

- Korrigiert die Umwandlung eingebetteter `\\n`-Marker in echte Zeilenumbrüche.
- Liest Wikipedia-Infobox-Besetzung zeilenweise statt mit einem übergreifenden Ausdruck.
- Zerlegt flache Besetzungslisten anhand ihrer Doppelpunkt-Blöcke.
- Trennt in mittleren Blöcken die vorherige Rolle vom nachfolgenden Schauspielernamen.
- Verhindert falsche Schauspielernamen wie `Mera Yahya Abdul-Mateen II`.
- Unterstützt Namenssuffixe wie `II`, `III`, `Jr.` und Initialen.
- Cast-Strategie auf `character_cast_intelligence_v4010` aktualisiert.

## 4.0.9 – Wikipedia Cast Pair Extraction Fix

- Erkennt Besetzungspaare aus eingebettetem Wikipedia-Infobox-Markup.
- Erkennt zusätzlich die flache Scanform `Schauspieler : Rolle`.
- Begrenzt Rollen zuverlässig am nächsten Schauspielernamen.
- Unterstützt Namen mit Suffixen wie `II`, `III` und `IV`.
- Erzeugt Personen-, Figuren- und Alias-Knoten sowie Cast-Kanten.
- Behebt `cast_pair_count: 0` trotz vorhandener Besetzungsliste.
- Cast-Strategie auf `character_cast_intelligence_v409` aktualisiert.

## 4.0.8 – Stable Version Regression Tests

- Entfernt fest codierte Patchversionsprüfungen aus älteren Knowledge-Graph-Funktionstests.
- Die Tests prüfen künftig eine gültige MediaHub-KI-Assistent-Version ab Hauptversion 4.
- Verhindert erneute Testfehler bei jedem regulären Patchversionswechsel.
- Laufzeitcode und Knowledge-Graph-Datenfluss aus v4.0.5 bis v4.0.7 bleiben unverändert.

## 4.0.7 – Dataflow Regression Version Update

- Aktualisiert den veralteten v4.0.5-Datenfluss-Test auf die aktuelle Plugin-Version.
- Behält den korrigierten Knowledge-Graph-Datenfluss unverändert bei.
- Verhindert Fehlmeldungen durch fest codierte alte Versionsnummern.

## 4.0.6 – Unified Graph Regression Test Update

- Aktualisiert den veralteten v4.0.4-Test auf den korrigierten v4.0.5-Datenfluss.
- Erwartet jetzt `knowledge_result=knowledge` statt der nicht definierten Variable.
- Prüft die aktuelle Plugin-Version 4.0.6.
- Behält alle v4.0.5-Laufzeitkorrekturen unverändert bei.

## 4.0.5 – Knowledge Graph Dataflow Fix

- Behebt `NameError: knowledge_result is not defined`.
- Verwendet die im Scan-Ablauf tatsächlich vorhandenen Variablen `knowledge`, `parsed`, `semantic` und `scan`.
- Baut den kanonischen Gesamtgraphen erst nach dem Universe-/Franchise-Merge.
- Nimmt Universe-/Franchise-Knoten und -Kanten ausdrücklich in den Gesamtgraphen auf.
- Bewahrt Hauptfilm, Vorgänger, Universum, Crew, Figuren, Events, Orte und Artefakte in einem Graphen.
- Automatische Übernahme bleibt deaktiviert und bestätigungspflichtig.

## 4.0.4 – Unified Base Graph Integration

- Übergibt den vorhandenen `knowledge_result`-Basisgraphen an den neuen kanonischen Graph-Builder.
- Führt Hauptfilm, Vorgänger, Universum, Crew, Events, Figuren, Orte und Artefakte in einem Gesamtgraphen zusammen.
- Übergibt zusätzlich Parser-, Semantic-, Classified- und Scan-Daten für die Legacy-Kompatibilität.
- Bewahrt `main_node_key` im neuen Knowledge-Graph.
- Verhindert einen isolierten Event-Graphen ohne Hauptmedium.
- Automatische Übernahme bleibt deaktiviert und bestätigungspflichtig.

## 4.0.3 – Graph Strategy Test Compatibility Cleanup

- Aktualisiert den veralteten v4.0.1-Regressionstest auf `knowledge_graph_builder_v402`.
- Behält die neue `knowledge_result`-Kompatibilität unverändert bei.
- Verhindert, dass ein korrekter Strategiewechsel als Funktionsfehler gemeldet wird.
- Ergänzt Regressionstests für neue, alte und kombinierte Builder-Eingänge.

## 4.0.2 – Knowledge Result Compatibility

- Akzeptiert den älteren Builder-Parameter `knowledge_result` wieder.
- Übernimmt Knoten aus `nodes`, `entity_nodes` oder `entity_proposals`.
- Übernimmt Kanten aus `edges`, `relation_edges` oder `relation_proposals`.
- Unterstützt verschachtelte Strukturen unter `graph` und `graph_proposal`.
- Führt alle übernommenen Daten anschließend durch den neuen kanonischen v4-Builder.
- Bestehende v2.9- und v4-Aufrufarten bleiben unverändert erhalten.

## 4.0.1 – Legacy Graph Builder Compatibility

- Stellt den bisherigen v2.9-Aufruf mit `parser_result`, `semantic_result`, `classified_fields` und `scan_result` wieder her.
- Bewahrt gleichzeitig den neuen v4-Aufruf mit `node_groups` und `edge_groups`.
- Erzeugt weiterhin Hauptmedium, Vorgänger, Universum, Universumswechsel und Crew-Knoten.
- Unterstützt die bisherigen Kanten `sequel_of`, `belongs_to`, `directed_by`, `music_by`, `cinematography_by` und `ends_with`.
- Bewahrt Laufzeit, FSK, Originaltitel und klassifizierte Felder am Hauptknoten.
- Beide Eingangswege werden anschließend vom neuen kanonischen Graph-Builder zusammengeführt.

## 4.0.0 – Knowledge Graph Engine Phase 1

- Führt einen eigenen `KnowledgeGraphBuilder` ein.
- Vereinheitlicht Knoten aus Event-, Relationship- und bestehenden Graph-Vorschlägen.
- Dedupliziert Knoten anhand kanonischer Knotenschlüssel.
- Dedupliziert Kanten anhand von Typ, Quelle und Ziel.
- Erzeugt fehlende Endpunktknoten als klar markierte Platzhaltervorschläge.
- Vergibt stabile IDs für Knoten und Kanten.
- Liefert Statistiken zu Knotenarten, Kantentypen und Platzhaltern.
- Speichert den erzeugten Graphen im Analyseergebnis und Dokumentkontext.
- Automatische Übernahme bleibt vollständig deaktiviert.

## 3.8.6 – Rescue Participant Final Boundary

- Schneidet Rettungsteilnehmer vor Präpositionen und nachfolgenden Satzteilen ab.
- Erkennt `Orm` statt `Orm aus dem Gefängnis`.
- Verhindert lange Fehlknoten mit nachfolgenden Sätzen oder Ortsangaben.
- Verwendet harte Grenzen vor `aus`, `vom`, `von`, `mit`, `bei`, `gegen`, `um`, `nach`, `in` und `auf`.
- Event-Strategie auf `event_intelligence_v386` aktualisiert.

## 3.8.5 – Character Candidate Capitalization Fix

- Verlangt bei kanonischen Figurennamen zwei tatsächlich großgeschriebene Namensbestandteile.
- Verwirft falsche Kandidaten wie `Orm aus`, `David hat` und `Arthur kämpft`.
- Behebt die fehlerhafte Umbenennung von `Orm` zu `Orm aus`.
- Behält gültige Namen wie `Arthur Curry`, `Orm Marius` und `David Kane` unverändert bei.
- Event-Strategie auf `event_intelligence_v385` aktualisiert.

## 3.8.4 – Character Name Candidate Boundary Fix

- Verhindert zusammengezogene Kandidaten wie `Arthur Curry David` und `David Kane Handlung`.
- Erkennt vollständige Figurennamen aus Alias-, Rollen- und Besetzungsformaten.
- Liest kompakte Besetzungsreihen paarweise statt als durchgehende Wortkette.
- Akzeptiert ausschließlich plausible zweiwortige kanonische Namen.
- Löst `Arthur`, `David` und `Orm` wieder zuverlässig auf ihre vollständigen Namen auf.
- `Arthur Jr.` bleibt weiterhin eine eigenständige Figur.

## 3.8.3 – Event Character Identity Resolver

- Führt kurze Ereignisnamen mit vollständigen Figurennamen aus demselben Artikel zusammen.
- Löst `Arthur` zu `Arthur Curry`, `David` zu `David Kane` und `Orm` zu `Orm Marius` auf, sofern der Artikel diese Namen belegt.
- Schützt Namen mit Suffix wie `Arthur Jr.` vor falscher Zusammenführung.
- Schreibt alle betroffenen Event-Kanten auf die neuen kanonischen Knotenschlüssel um.
- Führt identische Figurenknoten nach der Auflösung zusammen.
- Alle Identitätsauflösungen bleiben bestätigungspflichtig.

## 3.8.2 – Plot Cleaner Pipeline

- Führt einen eigenen `PlotCleaner` zwischen Abschnittsextraktion und Satzanalyse ein.
- Entfernt führende Überschriften wie `Handlung` vor der Figurenanalyse.
- Schneidet nachfolgende Abschnitte wie `Produktion`, `Synchronisation` und `Rezeption` zuverlässig ab.
- Entfernt Wikipedia-Marker wie `Bearbeiten | Quelltext bearbeiten`.
- Verhindert falsche Figuren wie `Handlung Arthur` und `Produktion James Wan`.
- Verbessert den Fallback auch für kurze Test- und Nicht-Wikipedia-Texte.
- Event-Strategie auf `event_intelligence_v382` aktualisiert.

## 3.8.1 – Wikipedia Plot Section Anchor Fix

- Ignoriert `Handlung` und `Produktion` aus dem Wikipedia-Inhaltsverzeichnis.
- Bevorzugt die echten Abschnittsüberschriften mit `Bearbeiten | Quelltext bearbeiten`.
- Verwendet bei Quellen ohne Abschnittsmarker den längsten plausiblen Handlungsteil.
- Behebt `event_count: 0` trotz vorhandenem vollständigem Handlungstext.
- Event-Strategie auf `event_intelligence_v381` aktualisiert.

## 3.8.0 – Battle Parser Rewrite

- Ersetzt die bisherige Kampf-Regex durch einen eigenen `BattleParser`.
- Erkennt normale deutsche Satzstellung wie `Arthur kämpft gegen David`.
- Erkennt invertierte Satzstellung wie `In Necrus kämpft Arthur gegen David`.
- Erkennt Ortsformen wie `Auf der Insel kämpfte Arthur gegen David`.
- Erkennt Kontextformen wie `Während der Schlacht kämpfte Thor gegen Hela`.
- Verknüpft erkannte Ortsangaben zuverlässig über `occurs_at`.
- Der BattleParser ist vollständig von Rettungs-, Entführungs- und Aliasregeln getrennt.

## 3.7.5 – German Event Word Order Fix

- Unterstützt Rettungssätze mit Subjekt vor dem Verb.
- Unterstützt Rettungssätze mit Verb vor dem Subjekt nach einem Nebensatz.
- Trennt führende Ortsangaben wie `In Necrus` vor der Figurenanalyse ab.
- Erkennt dadurch `Arthur`, `Orm`, `David`, `Arthur Jr.` und `Necrus` im gemeinsamen Realtest.
- Verhindert Figurenknoten mit Verwandtschaftsbegriffen oder Ortspräfixen.

## 3.7.4 – Kinship Rescue & Abbreviation Sentence Fix

- Erkennt `Arthur befreit seinen Halbbruder Orm` mit `Orm` als Figur.
- Speichert optionale Verwandtschaftsangaben am Rettungsereignis.
- Schützt Abkürzungen wie `Jr.`, `Dr.` und `Prof.` vor falscher Satztrennung.
- Erkennt dadurch `dass David Arthur Jr. entführt hat` wieder vollständig.
- Verhindert falsche Figuren wie `Halbbruder Orm`.

## 3.7.3 – Event Participant Boundary Fix

- Begrenzt Figuren vor den Präpositionen `aus`, `in`, `nach` und `mit`.
- Erkennt `Orm` statt `Orm aus dem Gefängnis`.
- Erkennt `Black Manta` statt `Black Manta in Necrus`.
- Stellt Orts- und Artefaktkanten für Sieg-Ereignisse wieder her.
- Ergänzt Regressionstests für reale Aquaman-Formulierungen.

## 3.7.2 – Real-World Event Sentence Parser

- Isoliert vor der Ereigniserkennung den Abschnitt `Handlung`.
- Wertet Ereignisse satzweise aus und verhindert Treffer über Satzgrenzen hinweg.
- Erkennt `befreit Arthur seinen Halbbruder Orm` als Rettungsereignis.
- Erkennt `dass David Arthur Jr. entführt hat` als Entführungsereignis.
- Erkennt `In Necrus kämpft Arthur gegen David` mit korrektem Ort.
- Verwirft Pronomen und unplausible Satzfragmente statt falsche Figuren anzulegen.

## 3.7.1 – Event Boundary Fix

- Begrenzt Kampfteilnehmer vor Orts- und Artefaktangaben.
- Erkennt in `Arthur Curry besiegte Black Manta in Necrus mit dem schwarzen Dreizack` jetzt Gegner, Ort und Artefakt getrennt.
- Stellt `occurs_at` und `uses` für Sieg- und Kampfereignisse wieder her.
- Ergänzt Regressionstests für Ereignisse mit und ohne Orts-/Artefaktangaben.

## 3.7.0 – Event Intelligence Phase 1

- Erzeugt eigene Ereignisknoten für Kämpfe und Siege.
- Erzeugt Ereignisknoten für Rettungen, Entführungen, Funde und Erschaffung von Artefakten.
- Verknüpft Figuren über `participates_in` bzw. `participant` mit Ereignissen.
- Verknüpft Ereignisse mit Orten über `occurs_at` oder `destination`.
- Verknüpft Ereignisse mit Artefakten über `uses` und `object`.
- Unterstützt `winner` und `loser` bei expliziten Sieg-Aussagen.
- Alle Ereignisse bleiben bestätigungspflichtige Vorschläge.

## 3.6.5 – Alias Test Compatibility Cleanup

- Aktualisiert die veraltete v3.6.3-Testannahme auf das korrigierte Verhalten aus v3.6.4.
- `David Kane ist auch bekannt als Black Manta` erwartet jetzt korrekt `David Kane` als Hauptfigur.
- Keine Laufzeitlogik geändert; ausschließlich Testkompatibilität und Versionsmetadaten bereinigt.

## 3.6.4 – Alias Reference Normalization Fix

- Entfernt Alias-Zusätze aus normalen Figurenreferenzen vor der Knotenerzeugung.
- Verhindert den falschen Knoten `character:arthur curry alias aquaman`.
- Allgemeine Regeln verwenden in Alias-Sätzen jetzt die Hauptfigur `Arthur Curry`.
- Bereinigt bei `ist auch bekannt als` das nachgestellte `ist` aus dem Hauptnamen.
- Der dedizierte Alias-Knoten und die `alias_of`-Beziehung bleiben unverändert erhalten.

## 3.6.3 – Dedicated Alias Parser

- Ersetzt die bisherige Alias-Regex durch einen eigenen `AliasParser`.
- Trennt explizit an `alias` und `auch bekannt als`.
- Schneidet nachfolgende Verben und Satzzeichen zuverlässig vom Alias ab.
- `Arthur Curry alias Aquaman verteidigte Atlantis` erzeugt exakt `Arthur Curry` und `Aquaman`.
- Alias-Erkennung ist vollständig von den allgemeinen Relationship-Regeln getrennt.
- Alle Ergebnisse bleiben bestätigungspflichtig.

## 3.6.2 – Relationship Parser Isolation Fix

- Stellt in der allgemeinen Relationship-Regelschleife `match.group(1)` und `match.group(2)` wieder her.
- Begrenzt die benannten Gruppen `primary` und `alias` ausschließlich auf den Alias-Parser.
- Behebt `IndexError: no such group` bei `works_with`, `rescues`, `kidnaps`, `fights_with` und `created_by`.
- Ergänzt Regressionstests für allgemeine Regeln und Alias-Regeln im selben Durchlauf.

## 3.6.1 – Alias Boundary Fix

- Begrenzt Aliasnamen vor nachfolgenden Verben und Satzzeichen.
- `Arthur Curry alias Aquaman verteidigte Atlantis` erzeugt jetzt exakt den Alias `Aquaman`.
- Verhindert falsche Alias-Knoten wie `Aquaman verteidigte Atlantis`.

## 3.6.0 – Relationship Intelligence Phase 2

- Erkennt Zusammenarbeit als `works_with`.
- Erkennt Rettung und Befreiung als `rescues` und `rescued_by`.
- Erkennt Kämpfe als symmetrisches `fights_with`.
- Erkennt Entführungen als `kidnaps` und `kidnapped_by`.
- Erkennt Schutzbeziehungen als `protects`.
- Erkennt Artefakterzeugung als `created_by` und `creates`.
- Erkennt Alias-Aussagen aus Handlungstexten.
- Erkennt Funde von Artefakten als `finds`.
- Alle Ergebnisse bleiben bestätigungspflichtig.

## 3.5.0 – Character Intelligence Phase 1

- Erkennt Ehebeziehungen als `married_to` in beide Richtungen.
- Erkennt Eltern-/Kind-Beziehungen als `parent_of` und `child_of`.
- Erkennt Geschwisterbeziehungen als symmetrisches `sibling_of`.
- Erkennt einfache Feind- und Verbündetenbeziehungen.
- Erkennt Herrscherbeziehungen als `ruler_of`.
- Erzeugt aus sicheren Ortsaussagen `lives_in`.
- Alle Ergebnisse bleiben bestätigungspflichtig.

## 3.4.0 – Character & Cast Intelligence Phase 2

- Erzeugt `has_cast` vom Medium zur besetzten Person.
- Erzeugt `portrays` von der Person zur Figur und weiterhin `portrayed_by` in Gegenrichtung.
- Erkennt Rollen-Aliase wie `Arthur Curry / Aquaman` als getrennte Alias-Knoten.
- Speichert Besetzungsposition, Rohrollenname und Quellenformat als Metadaten.
- Erkennt Sprachrollen mit `(Stimme)` und erzeugt zusätzlich `voices`.
- Nutzt weiterhin den eindeutigen Hauptmedium-Schlüssel inklusive Erscheinungsjahr.
- Alle Graph-Ergebnisse bleiben bestätigungspflichtig.

## 3.3.3 – Graph Integration Cleanup

- Bereinigt reale Formulierungen wie `und letzte Film des DC Extended Universe`.
- Unterdrückt falsche Film-Ortsbeziehungen zu `Atlantis geworden war`.
- Liest Wikipedia-Besetzungen aus dem eingebetteten Infobox-Wikitext.
- Stellt Personen-, Figuren- und Alias-Knoten aus dem Aquaman-Scan wieder her.
- Vereinheitlicht Hauptfilm-Schlüssel mit Erscheinungsjahr in allen Teilmodulen.
- Alle Ergebnisse bleiben bestätigungspflichtig.

## 3.3.2 – Universe Replacement Edge Fix

- Normalisiert jetzt auch den Startknoten einer `replaced_by`-Beziehung.
- Verhindert den falschen Schlüssel `universe:der letzte film des dc extended universe`.
- Die Kante lautet jetzt korrekt `universe:dc extended universe --replaced_by--> universe:dc universe`.
- Die Namensnormalisierung aus v3.3.1 bleibt unverändert erhalten.

## 3.3.1 – Universe Name Normalization Fix

- Entfernt führende Wörter wie `das`, `Teil des` oder `letzte Film des` aus Universumsnamen.
- Verhindert falsche Knoten wie `universe:das dc universe`.
- Verhindert vollständige Satzfragmente als Universumsnamen.
- Universumswechsel erkennt jetzt exakt `DC Extended Universe` und `DC Universe`.

## 3.3.0 – Universe & Franchise Builder Phase 1

- Neue Knoten für Universen, Franchises, Teams, Orte und Organisationen.
- Beziehungen belongs_to, part_of, member_of, replaced_by und located_in.
- Einfache ally_of- und enemy_of-Erkennung.
- Universumswechsel wie DCEU -> DC Universe werden strukturiert erfasst.
- Ergebnisse werden mit dem bestehenden Graph-Vorschlag zusammengeführt.
- Weiterhin keine automatische Übernahme ohne Bestätigung.

## 3.2.0 – Character & Cast Resolver Phase 1

- Rollen wie Arthur Curry / Aquaman werden in Hauptfigur und Alias zerlegt.
- Neue Knotentypen person, character und character_alias.
- Neue Beziehungen portrayed_by, appears_in und alias_of.
- Cast-Ergebnisse werden mit dem Graph-Vorschlag zusammengeführt.
- Weiterhin keine automatische Übernahme ohne Bestätigung.

## 3.1.0 – Relationship Builder Phase 1

- Explizite Fortsetzungs-, Prequel- und Spin-off-Beziehungen.
- Automatische Zielknoten für erwähnte Werke.
- Personen- und Figurenknoten aus Besetzungslisten.
- Beziehungen appears_in und portrayed_by.
- Zusammenführung mit dem normalen Graph-Vorschlag.
- Weiterhin keine automatische Übernahme ohne Bestätigung.

## 3.0.0 – Persistenter Knowledge Graph Phase 1

- Dauerhaft gespeicherter Knowledge Graph.
- Vorschau für neue, bestehende und aktualisierbare Knoten und Kanten.
- Bestätigte Übernahme mit Dubletten-Zusammenführung.
- Alias-Index, Änderungsverlauf und Knotensuche.
- Neuer Button „Persistenter Graph-Status“.
- Keine automatische Übernahme ohne Bestätigung.

## 2.9.0 – Knowledge Graph Builder Phase 1

- Erzeugt bestätigungspflichtige Graph-Knoten und -Kanten.
- Unterstützt Hauptmedium, Vorgänger, Universum, Personen und Ereignisse.
- Beziehungen: sequel_of, belongs_to, directed_by, music_by, cinematography_by und ends_with.
- Laufzeit, FSK und Originaltitel werden am Hauptknoten gespeichert.
- Neuer Button „Graph-Builder-Status“.

## 2.8.0 – Semantic Field Classification

- Jahreszahlen werden nach Bedeutung klassifiziert.
- Erscheinungsjahr, Produktionsjahr, geplanter Kinostart und Universumswechsel werden getrennt.
- Vorgängerfilme werden mit Titel und Jahr strukturiert ausgegeben.
- Der Hauptfilm erhält ein eindeutiges `release_year`.
- Bild- und Artwork-Jahre werden verworfen.
- Neuer Button „Field-Classifier-Status“.

## 2.7.3 – Reasoning Context Phase 1

- Gemeinsames internes Arbeitsobjekt für Scanner, Parser, Semantic Engine und Knowledge Extractor.
- Speichert Entitäten, Beziehungen, Kandidaten, Belege, Annahmen, Ablehnungen, offene Fragen und nächste Aufgaben.
- Cosplay-, Poster-, Cover-, Screenshot-, Logo- und Artwork-Kontexte werden als verdächtig verworfen.
- Analyseablauf wird als technische Trace-Liste protokolliert.
- Reasoning Contexts werden getrennt vom Knowledge Graph als JSON gespeichert.
- Neuer Button „Reasoning-Context-Status“.

## 2.7.2 – Legacy Year Pattern Fix

- Die rückwärtskompatible Jahreserkennung versteht jetzt Sätze, bei denen das Jahr vor dem Verb steht.
- Beispiel: „Im Dezember 2018 erschien der Film Aquaman“ wird korrekt als 2018 erkannt.
- Der semantische Mehrentitäten-Ablauf bleibt unverändert.
- Der Fix betrifft ausschließlich alte Extractor-Aufrufe ohne `semantic_result`.

## 2.7.1 – Semantic Compatibility Fix

- Der Knowledge Extractor unterstützt ältere Aufrufe ohne `semantic_result` weiterhin.
- Ohne Semantic-Ergebnis wird ausschließlich für Kompatibilität die bisherige kontextbezogene Jahresauswahl verwendet.
- Mit Semantic-Ergebnis bleibt die Semantic Engine verbindlich; es gibt keine alte Überschreibung.
- Neue Filmsatz-Muster erkennen Formulierungen wie „Im Dezember 2018 erschien der Film Aquaman“.
- Die Regressionstests aus v2.6.7 und v2.6.8 bleiben dadurch gültig.
- Der neue semantische Mehrentitäten-Ablauf aus v2.7.0 bleibt unverändert erhalten.

## 2.7.0 – Semantic Knowledge Extractor Phase 2

- Die Semantic Knowledge Engine bestimmt verbindlich Entitätstypen und Jahreszuordnungen.
- Der alte Extractor trifft keine eigenen Jahresentscheidungen mehr.
- Figur, Film und Serie mit gleichem Namen werden als getrennte Entitäten ausgegeben.
- Das Jahr wird nur der passenden Kombination aus Titel und Entitätstyp zugeordnet.
- Die alte Plugin-Nachbearbeitung, die korrekte Semantic-Ergebnisse überschreiben konnte, wurde entfernt.
- Aquaman als Figur erhält kein falsches Jahr 2017.
- Aquaman als Film erhält 2018 und die Zeichentrickserie erhält 1967.
- Alle Vorschläge bleiben bestätigungspflichtig.

## 2.6.8 – Semantic Knowledge Engine Phase 1

- Satzbasierte Semantikanalyse zwischen Parser und Knowledge Extractor.
- Primärer Entitätstyp wird als Figur, Film, Serie, Hörbuch, Verlag oder Universum erkannt.
- Jahreszahlen werden nur bei gemeinsamem Satzkontext von Titel, Typ und Jahr zugeordnet.
- Mehrere Entitäts- und Beziehungsvorschläge pro Quelle.
- Kein automatischer Import; alle Ergebnisse bleiben bestätigungspflichtig.
- Neuer GUI-Button „Semantic-Engine-Status“.

## 2.6.7 – Knowledge Extractor Phase 1

- Neuer Knowledge Extractor hinter dem Parser Manager.
- Parser-Felder werden in bestätigbare Feld-, Entitäts-, Gruppen- und Beziehungsvorschläge umgewandelt.
- Jahreszahlen werden nicht mehr blind übernommen; ein Jahr wird nur bei eindeutigem Titel- oder Veröffentlichungskontext vorgeschlagen.
- Mehrdeutige Jahreslisten bleiben als schwache Kandidaten sichtbar und erfordern manuelle Auswahl.
- Universums- und Franchiseangaben erzeugen eigene Gruppenmitgliedschaftsvorschläge.
- Mögliche Nachfolger werden als Beziehungsvorschläge ausgegeben.
- Sämtliche Ergebnisse bleiben Importvorschauen und werden niemals automatisch in den Knowledge Graph geschrieben.
- Neuer GUI-Button „Knowledge-Extractor-Status“.

## 2.6.6 – Parser Manager Phase 1

- Neue zentrale Parser-Registry mit Prioritäten und Unterstützungsregeln.
- Generischer HTML-Parser für beliebige öffentliche Webseiten.
- Eigener Wikipedia-Parser mit bereinigtem Seitentitel und ersten medienbezogenen Strukturhinweisen.
- Parser werden automatisch anhand von Quellentyp und Domain ausgewählt.
- Parser-Ergebnisse besitzen ein einheitliches Schema mit Feldern, Konfidenz, Einschränkungen und Quellenbezug.
- Kontrollierte Webseiten-Scans werden jetzt zusätzlich durch den Parser Manager verarbeitet.
- Parser-Ergebnisse werden ausschließlich als bestätigungspflichtige Importvorschau gespeichert.
- Neuer GUI-Button „Parser-Status“.

## 2.6.5 – Professionelle Quellenverwaltung

- Die Quellenauswahl ist jetzt deutlich mit „Vorhandene Quelle auswählen“ beschriftet.
- Beim Wechsel der Auswahl werden Name, URL, Kategorie, Vertrauen, Priorität, Status und Quellentyp automatisch geladen.
- Policy-Diagnose, Scan-Vorschau und kontrollierter Scan verwenden dadurch eindeutig die ausgewählte Quelle.
- Neue Aktionen: „Neue Quelle“, „Als eigene Quelle speichern“, „Änderungen speichern“ und „Ausgewählte Quelle löschen“.
- Vordefinierte Quellen können deaktiviert, aber nicht versehentlich gelöscht werden.
- Benutzerdefinierte Quellen können bearbeitet und nach Sicherheitsabfrage gelöscht werden.
- Die Quellenübersicht wurde kompakter gestaltet, damit Konflikt- und Feldübernahmebereiche besser sichtbar bleiben.

## 2.6.4 – Source Policy Debug Engine

- robots.txt wird jetzt mit eigener HTTP-Diagnose geladen und ausgewertet.
- Unterscheidung zwischen `allowed`, `blocked`, `robots_missing`, `unknown`, `network_error` und `timeout`.
- HTTP-Status, Inhaltstyp, User-Agent und robots.txt-Auszug werden angezeigt.
- HTTP 404 für robots.txt gilt nicht mehr automatisch als Verbot.
- Netzwerkfehler und Timeouts werden nicht mehr fälschlich als ausdrückliche Sperre dargestellt.
- Neuer GUI-Button „Policy-Diagnose“.
- Bei abgebrochenen Scans wird die vollständige Diagnose angezeigt.

## 2.6.3 – Source Manager Phase 4

- Quellenvergleiche füllen die empfohlenen Felder automatisch als bearbeitbares JSON-Objekt vor.
- Benutzer können einzelne Felder entfernen, ändern oder ergänzen.
- Eine Ziel-Entität aus dem Knowledge Graph kann direkt ausgewählt werden.
- Vor der Übernahme wird eine vollständige Vorher-/Nachher-Vorschau angezeigt.
- Die tatsächliche Übernahme benötigt eine zusätzliche Sicherheitsabfrage.
- Bestätigte Kernfelder und Metadaten werden kontrolliert in die Ziel-Entität geschrieben.
- Der Knowledge Graph wird nach erfolgreicher Übernahme sofort aktualisiert.

## 2.6.2 – Source Manager Phase 3

- Mehrere Quellenergebnisse können feldweise verglichen werden.
- Abweichende Titel, Jahre, Medientypen, Beziehungen und sonstige Felder werden als Konflikte markiert.
- Empfehlungen berücksichtigen Vertrauenswert, Priorität und Anzahl unabhängiger Unterstützer.
- Jedes Feld bleibt einzeln bestätigungspflichtig.
- Bestätigte Felder können kontrolliert in eine vorhandene Knowledge-Graph-Entität übernommen werden.
- Vergleiche und Entscheidungen werden lokal protokolliert.
- Neuer GUI-Bereich „Quellenkonflikte“.

## 2.6.1 – Source Manager Phase 2

- Kontrolliertes Laden öffentlicher Webseiten über HTTP/HTTPS.
- robots.txt wird vor dem Abruf geprüft.
- Bei unbekanntem Richtlinienstatus wird standardmäßig abgebrochen.
- Größenlimit, Timeout und erlaubter Inhaltstyp schützen vor ungeeigneten Seiten.
- Geladene Seiten werden lokal zwischengespeichert.
- Extrahiert werden Seitentitel, Überschriften, Links, Jahreszahlen, Staffel-/Folgenhinweise und mögliche Beziehungsschlüsselwörter.
- Ergebnisse werden ausschließlich als strukturierte Importvorschau gespeichert.
- Kein automatischer Import in den Knowledge Graph.
- Neuer GUI-Button „Quelle kontrolliert scannen“.

## 2.6.0 – Source Manager Phase 1

- Zentrale Quellenverwaltung für APIs, Webseiten, benutzerdefinierte URLs, lokale Caches, Knowledge Packs und Provider.
- Vordefinierte Grundquellen: TMDb, TheTVDB, Wikidata, Wikipedia und lokaler Cache.
- Eigene Webseiten können mit Name, URL, Kategorie, Priorität und Vertrauenswert gespeichert werden.
- Quellen können aktiviert, deaktiviert und priorisiert werden.
- Jede Quelle besitzt Cache-, Sprach-, Regions- und Vertrauensmetadaten.
- Source-Scans erzeugen in Phase 1 ausschließlich einen kontrollierten Ausführungsplan.
- Netzwerkzugriffe, Seitenextraktion und Importe werden noch nicht automatisch gestartet.
- Jeder spätere Import benötigt eine Vorschau und ausdrückliche Bestätigung.
- Neue GUI-Registerkarte „Quellen“.

## 2.5.2 – Lernen aus Reasoner-Entscheidungen

- Bestätigte, abgelehnte und zurückgestellte Vorschläge werden als Lernsignale gespeichert.
- Beziehungstypen und Belegarten erhalten getrennte Erfolgsstatistiken.
- Wiederholt bestätigte Muster können die Konfidenz ähnlicher Vorschläge leicht erhöhen.
- Wiederholt abgelehnte Muster können die Konfidenz ähnlicher Vorschläge leicht senken.
- Die Lernanpassung ist bewusst begrenzt und kann keine schwache Vermutung automatisch in eine sichere Entscheidung verwandeln.
- Vorschläge bleiben immer bestätigungspflichtig.
- Neuer GUI-Button „Reasoner-Lernstatus“.
- Die Reasoner-Ausgabe zeigt Basiskonfidenz und Lernanpassung getrennt.

## 2.5.1 – Semantic Graph Reasoner, Phase 2

- Neue Vorschläge für Prequel, Spin-off, Crossover, Backdoor-Pilot und Reboot.
- Bestätigte Metadaten wie `parent_title`, `origin_title`, `is_prequel`, `is_spin_off`, `is_backdoor_pilot`, `is_reboot` und `crossover_with` werden ausgewertet.
- Titelmuster wie „Origins“, „Origin“, „Beginnings“ oder „Before“ können zusammen mit einem bestätigten Ursprungstitel einen Prequel-Vorschlag begründen.
- Gemeinsame Figuren plus gemeinsames Universum können eine erklärbare Verwandtschaftsbeziehung erzeugen.
- Alle Vorschläge bleiben bestätigungspflichtig und werden nicht automatisch gespeichert.

## 2.5.0 – Semantic Graph Reasoner, Phase 1

- Neuer konservativer Reasoner für erklärbare Knowledge-Graph-Vorschläge.
- Bestätigte Franchise- und Universumsmetadaten erzeugen Gruppenmitgliedschaftsvorschläge.
- Bestätigte `relation_hints` werden als starke direkte Beziehungsvorschläge ausgewertet.
- Titelnummern, gemeinsame Gruppen, Veröffentlichungsjahre und gespeicherte Reihenfolgen können gemeinsam einen Sequel-Vorschlag begründen.
- Vorschläge unterhalb der Mindestkonfidenz werden verworfen.
- Bereits vorhandene Beziehungen werden nicht erneut vorgeschlagen.
- Jeder Vorschlag enthält Konfidenz, Belege und eine verständliche Begründung.
- Sämtliche Ergebnisse landen nur in der bestehenden Vorschlagswarteschlange und benötigen Benutzerbestätigung.
- Neuer GUI-Button „Graph analysieren“.

## 2.4.6 – Graph-basierte Vollständigkeit und lesbare Anzeige

- Die Vollständigkeitsprüfung verwendet jetzt Gruppenmetadaten, bestätigte Gruppenbeziehungen und gespeicherte Reihenfolgen.
- Eine gespeicherte Veröffentlichungs- oder chronologische Reihenfolge wird als prüfbare Gruppe erkannt.
- Ohne separate Soll-Liste gelten bestätigte Gruppenmitglieder vorläufig als vollständiger Bestand; diese Einschränkung wird transparent angezeigt.
- Beziehungen werden mit Titeln und Jahren statt interner UUIDs dargestellt.
- Reihenfolgen werden nummeriert und mit lesbaren Titeln angezeigt.
- Die Vollständigkeitsausgabe zeigt vorhandene Teile, fehlende Teile und einen klaren Status „Vollständig“ oder „Unvollständig“.

## 2.4.5 – Identitäten bereinigen und zusammenführen

- Falsche oder doppelte Graph-Entitäten können sicher entfernt werden.
- Ein falscher Eintrag kann in einen korrekten Eintrag zusammengeführt werden.
- Vor jeder Änderung wird eine vollständige Vorschau angezeigt.
- Vor der Ausführung werden Wissensdatenbank und Knowledge Graph automatisch gesichert.
- Aliase, Fingerprint-Verweise und Visual Knowledge werden beim Zusammenführen auf das Ziel übertragen.
- Graph-Beziehungen und Reihenfolgen werden auf die behaltene Entität umgeleitet.
- Beim reinen Löschen werden verwaiste Beziehungen und Reihenfolgeneinträge entfernt.
- Doppelte Beziehungen werden nach einer Zusammenführung bereinigt.

## 2.4.4 – Rückmeldungsimport und Abschluss des Fehlende-Medien-Blocks

- Rückmeldungen anderer Plugins können als JSON-Datei importiert werden.
- Einzelne Ergebnisobjekte und Ergebnislisten werden unterstützt.
- Gültige Rückmeldungen werden kontrolliert übernommen; fehlerhafte Einträge werden separat ausgewiesen.
- Die GUI zeigt einen gemeinsamen Status für Warteschlange, Übergaben, Rückmeldungen und offene Einträge.
- Nach dem Import werden Warteschlange und Knowledge Graph aktualisiert.
- Automatische Downloads, Websuchen und Dateiänderungen bleiben deaktiviert.
- Damit ist der erste vollständige Fehlende-Medien-Workflow abgeschlossen.

## 2.4.3 – Sichere Plugin-Übergabe für fehlende Medien

- Fehlende-Medien-Einträge können gezielt an ein anderes MediaHub-Plugin übergeben werden.
- Jede Übergabe erhält eine eindeutige `handoff_id` und ein versioniertes JSON-Schema.
- Empfängerplugins erhalten keine direkte Schreibberechtigung auf die Warteschlange.
- Rückmeldungen werden validiert und kontrolliert in Warteschlangenstatus übersetzt.
- Übergaben und Rückmeldungen werden in einem lokalen Audit-Log protokolliert.
- Automatische Downloads, Websuchen und Dateiänderungen bleiben ausdrücklich deaktiviert.
- Die GUI kann Übergabedateien direkt als JSON speichern.

## 2.4.2 – Fehlende-Medien-Export und Plugin-Übergabe

- Offene und als gesucht markierte fehlende Medien können als JSON oder CSV exportiert werden.
- Das JSON-Format enthält ein versioniertes Übergabeschema für spätere MediaHub-Plugins.
- CSV-Exporte enthalten Status, Gruppe, Titel, Jahr, Medientyp und Notizen.
- Der Export enthält ausschließlich offene, gesuchte oder zurückgestellte Einträge.
- Es werden keine Downloads, Websuchen oder Dateiänderungen ausgelöst.
- Die GUI bietet einen direkten Exportdialog für JSON und CSV.

## 2.4.1 – Automatische Auflösung fehlender Medien

- Offene Fehlende-Medien-Einträge werden automatisch als vorhanden markiert, sobald eine passende bestätigte Graph-Entität existiert.
- Der Abgleich berücksichtigt den Haupttitel und bestätigte Aliase.
- Jahr und Medientyp werden berücksichtigt, sofern sie auf beiden Seiten vorhanden sind.
- Die Auflösung erfolgt nach Benutzerbestätigung, manueller Entitätserstellung und beim Aktualisieren des Knowledge Graph.
- Abgelehnte oder bereits erledigte Einträge werden nicht verändert.
- Die Graph-Übersicht zeigt, wie viele fehlende Medien beim aktuellen Abgleich aufgelöst wurden.
- Es werden weiterhin keine Downloads oder Dateiveränderungen ausgeführt.

## 2.4.0 – Fehlende-Medien-Warteschlange

- Fehlende Teile aus der Vollständigkeitsprüfung werden dauerhaft als Aufgaben gespeichert.
- Einträge können als gesucht, nicht benötigt, später prüfen oder bereits vorhanden markiert werden.
- Die Warteschlange bleibt nach einem MediaHub-Neustart erhalten.
- Doppelte Einträge werden vermieden.
- Es werden keine Downloads, Dateisuche oder Dateiveränderungen automatisch ausgeführt.
- Die vollständige Warteschlange kann in einem scrollbarfähigen Fenster angezeigt werden.
- Die Vollständigkeitsprüfung zeigt, wie viele neue Aufgaben erzeugt wurden.

## 2.3.9 – Franchise- und Reihenfolgen-Vollständigkeit

- Franchise- und Universumsgruppen können gegen eine bestätigte Soll-Liste geprüft werden.
- Fehlende Filme, Serien, Episoden oder Hörbücher werden als reine Hinweise ausgegeben.
- Die Prüfung verändert weder Dateien noch Graph-Einträge.
- Manuell angelegte Entitäten können eine zeilenweise Soll-Liste erwarteter Teile speichern.
- Ohne bestätigte Soll-Liste wird transparent angezeigt, dass keine abschließende Vollständigkeitsbewertung möglich ist.
- Die Auswertung erscheint in einem scrollbarfähigen Fenster.

## 2.3.8 – Bestätigbare Reihenfolge-Vorschläge

- Aus Franchise- und Universumsmetadaten werden Veröffentlichungsreihenfolgen vorgeschlagen.
- Veröffentlichungsreihenfolgen werden nach bestätigtem Erscheinungsjahr sortiert.
- Chronologische Reihenfolgen werden vorgeschlagen, wenn alle beteiligten Entitäten einen bestätigten `chronology_index` besitzen.
- Vorschläge landen in derselben persistenten Warteschlange wie Beziehungsvorschläge.
- Reihenfolgen werden erst nach ausdrücklicher Bestätigung gespeichert.
- Bereits vorhandene identische Reihenfolgen werden nicht doppelt erzeugt.

## 2.3.7 – Automatische Knowledge-Graph-Vorschläge

- Die GUI kann Vorschläge direkt aus vorhandenen Graph-Entitäten und deren Metadaten erzeugen.
- Manuell angelegte Entitäten können ein Franchise und ein Universum speichern.
- Ein neuer Button „Automatisch vorschlagen“ erzeugt bestätigbare Gruppen- und Beziehungsvorschläge.
- Vorschläge werden weiterhin nur in die Warteschlange geschrieben und niemals automatisch übernommen.
- Bereits bekannte Vorschläge werden erkannt und nicht doppelt angelegt.
- Die Vorschlagsausgabe bleibt vollständig nachvollziehbar und scrollbar.

## 2.3.6 – Franchise- und Universums-Vorschläge übernehmen

- Vorschläge vom Typ `group_membership` können jetzt bestätigt werden.
- Beim Bestätigen wird das Franchise, Universum oder die Sammlung automatisch als eigene Graph-Entität angelegt.
- Das erkannte Medium wird anschließend über die vorgeschlagene Beziehung mit dieser Gruppenentität verbunden.
- Bereits vorhandene Franchise- oder Universumsentitäten werden wiederverwendet und nicht doppelt angelegt.
- Direkte Beziehungen wie Sequel, Prequel, Spin-off und Crossover funktionieren unverändert weiter.
- Die Vorschlagsliste zeigt Gruppenmitgliedschaften jetzt im gleichen verständlichen Pfeilformat wie direkte Beziehungen.

## 2.3.5 – Persistente Knowledge-Graph-Vorschlagsliste

- Beziehungsvorschläge werden dauerhaft in einer lokalen Warteschlange gespeichert.
- Offene Vorschläge bleiben nach einem MediaHub-Neustart erhalten.
- Direkte Beziehungsvorschläge können ausdrücklich bestätigt und gespeichert werden.
- Vorschläge können abgelehnt oder zur späteren Prüfung zurückgestellt werden.
- Bereits bekannte Vorschläge werden nicht doppelt in die Warteschlange aufgenommen.
- Abgelehnte Vorschläge erscheinen nicht erneut als offene Aufgabe.
- Der veraltete v2.3.1-GUI-Test wurde auf die scrollbare Oberfläche aktualisiert.

## 2.3.4 – Scrollbare KI-Assistent-Oberfläche

- Die vollständige Registerkarte „Knowledge Graph“ liegt jetzt in einem QScrollArea.
- Die Registerkarte „Dateianalyse & Lernen“ ist ebenfalls vollständig scrollbar.
- Vertikale und horizontale Scrollbalken erscheinen automatisch, sobald der Inhalt nicht in das Fenster passt.
- Die Oberfläche bleibt dadurch auch auf kleineren Bildschirmen vollständig bedienbar.
- Die bereits vorhandenen scrollbarfähigen Statusdialoge bleiben unverändert erhalten.

## 2.3.3 – Komfortable Knowledge-Graph-Bedienung

- Entitäten können direkt über Titel, Medientyp, Jahr und Aliase angelegt werden.
- Reihenfolgen verwenden Titel oder IDs zeilenweise statt langer ID-Listen.
- Die Graph-Übersicht zeigt IDs von Beziehungen und Reihenfolgen.
- Beziehungen und Reihenfolgen können nach Sicherheitsabfrage gezielt gelöscht werden.
- Lange Ergebnisse bleiben in scrollbarfähigen Dialogen.

## 2.3.2 – Scrollbare Statusfenster und Lern-Datenmigration

- Lange Status-, JSON- und Ergebnisdialoge werden in einem begrenzten, größenveränderbaren Fenster mit vertikaler und horizontaler Bildlaufleiste angezeigt.
- Knowledge-Graph-Status, Lernstatus, gespeicherte Beziehungen und Reihenfolgen sprengen nicht mehr die Bildschirmhöhe.
- Bereits vor v2.3.0 gelernte Identitäten werden automatisch und idempotent in den Knowledge Graph übernommen.
- Die Graph-Übersicht zeigt, wie viele gelernte Identitäten geprüft und neu übernommen wurden.
- Die Migration verändert keine bestehenden Lern-Daten und erzeugt keine doppelten Graph-Entitäten.

## 2.3.1 – Sichtbare Knowledge-Graph-Verwaltung

- Neue Desktop-Registerkarte „Knowledge Graph“.
- Entitäten, Aliase, Medientypen, Beziehungen und Reihenfolgen werden sichtbar dargestellt.
- Die Übersicht kann nach Titel, Alias oder Medientyp gefiltert werden.
- Beziehungen lassen sich erst nach ausdrücklicher Sicherheitsabfrage speichern.
- Beziehungsvorschläge können als JSON geprüft werden; sie werden nie automatisch gespeichert.
- Veröffentlichungs-, chronologische, Anschau- und eigene Reihenfolgen können angelegt werden.
- Quelle und Ziel einer Beziehung werden aus den vorhandenen Graph-Entitäten gewählt.

## 2.3.0 – Knowledge Graph Builder, Phase 1

- Benutzerbestätigte Medienidentitäten werden automatisch und idempotent als Graph-Entitäten übernommen.
- Doppelte Entitäten werden über externe IDs, Titel, Alias, Medientyp und Jahr vermieden.
- Aliase, externe IDs und Metadaten vorhandener Entitäten werden zerstörungsfrei ergänzt.
- Beziehungen wie Franchise, Universum, Spin-off, Prequel, Sequel und Crossover können bestätigt gespeichert werden.
- Veröffentlichungs-, Chronologie-, Anschau- und benutzerdefinierte Reihenfolgen werden idempotent angelegt.
- Metadaten können erklärbare Beziehungsvorschläge erzeugen; Vorschläge werden niemals automatisch als Beziehung gespeichert.
- Bestätigtes Lernen verbindet die lokale Medienidentität direkt mit dem Knowledge Graph.

## 2.2.9 – Semantic Output Priority

- Die sichtbare Erkennungsausgabe verwendet zuerst die finale Semantic Identity.
- Bestätigte Fingerprint-Treffer übersteuern den alten Dateinamen-Vorschlag.
- Titel, Jahr, Medientyp, Staffel, Episode und Fassung stammen aus der stärksten bestätigten Identität.
- Der Dateiname bleibt nur noch als letzter Fallback erhalten.
- Die primäre Identitätsquelle wird ausdrücklich angezeigt.
- Die Integration-API wurde auf Produzentenversion 2.2.9 aktualisiert.

## 2.2.8 – Erste Desktop-GUI für semantische Identität und Lernen

- Die bestehende MediaHub-KI-Assistent-Oberfläche wurde um einen vollständigen Bestätigungsbereich erweitert.
- Unsichere Analyseergebnisse können als Film, Serie, Episode oder Hörbuch korrigiert werden.
- Titel, Jahr, Staffel, Episode und Fassung sind direkt bearbeitbar.
- Die Schaltfläche „Identität bestätigen und lernen“ speichert die Zuordnung erst nach einer Sicherheitsabfrage.
- Gespeicherter Fingerprint, Visual Knowledge und Wissensdatenbankpfad werden sichtbar bestätigt.
- Ein Lernstatus zeigt Identitäten, Aliase, Fingerprint-Referenzen, Visual Knowledge und Konflikte.
- Die aktuell ausgewählte Datei kann nach dem Lernen direkt erneut analysiert werden.

## 2.2.7 – Confirmed Fingerprint & Visual Learning

- Die bestehende Benutzerbestätigung speichert Identität, Aliase und Video-Fingerprint gemeinsam.
- Bestätigte Visual-Intelligence-Daten werden zusätzlich als Visual Knowledge gespeichert.
- Die Rückgabe nennt den exakten Pfad der verwendeten Wissensdatenbank.
- Ein neuer Lernstatus zeigt Identitäten, Aliase, Fingerprint-Referenzen, Visual-Knowledge-Einträge und Konflikte.
- Die Integration-API verwendet bevorzugt die finale Semantic Identity.
- Automatisches Lernen bleibt gesperrt; Lernen erfolgt nur nach ausdrücklicher Benutzerbestätigung oder späterer sicherer Orchestrator-Freigabe.

## 2.2.6 – Semantic Identity Evidence Bridge

- Rohe Analysemerkmale werden nicht länger fälschlich als Identitätsbelege behandelt.
- Video-Fingerprints werden direkt gegen die lokale Referenzdatenbank geprüft.
- Bestätigte Visual-Knowledge-Signaturen werden einer gespeicherten Medienidentität zugeordnet.
- Gelernte Titel und Aliasnamen bleiben als lokale Wissensbelege verfügbar.
- Bei Cache-Treffern wird der Online-Abgleich erneut ausgeführt, solange keine bestätigte semantische Identität vorliegt.
- OCR-Zeichensalat bleibt ausgeschlossen; nur akzeptierte Titelkarten-Kandidaten werden übernommen.

## 2.2.5 – Semantic Identity Engine

- Candidate Builder, Evidence Collector, Contradiction Detector, Confidence Calculator und Explainable Decision wurden zu einer vollständigen Engine verbunden.
- Die Engine liefert erstmals einen finalen semantischen Identitätsstatus.
- Unterstützte Endzustände: `unknown`, `candidate`, `possible`, `probable` und `confirmed`.
- Automatische Bestätigung erfordert mindestens 92 Prozent Vertrauen, drei unabhängige Beleggruppen und ausreichenden Abstand zum zweitbesten Kandidaten.
- Kritische Konflikte verhindern eine Bestätigung.
- Lernen ist nur bei bestätigter, konfliktfreier Identität ohne weitere Benutzerbestätigung erlaubt.
- Die finale Entscheidung bleibt vollständig erklärbar und enthält eine klare Begründung.

## 2.2.4 – Semantic Identity Explainable Decision

- Jeder Kandidat erhält eine verständliche Begründung seiner semantischen Einstufung.
- Verwendete Hauptbelege, zusätzliche Belege und fehlende Beleggruppen werden getrennt dargestellt.
- Konflikte, Abzüge und Konkurrenzunsicherheit bleiben vollständig sichtbar.
- Die Erklärung enthält Vertrauenswert, Status, Schlussfolgerung und konkrete Empfehlung.
- Die Ausgabe ist für die spätere Darstellung in der MediaHub-GUI vorbereitet.
- Die Engine erklärt weiterhin nur; die finale Identitätsentscheidung folgt in v2.2.5.

## 2.2.3 – Semantic Identity Confidence Calculator

- Belegstärke und Kandidatenstruktur werden zu einem vorsichtigen Vertrauenswert kombiniert.
- Mehrere wirklich unabhängige Beleggruppen erhalten einen begrenzten Bonus.
- Konflikt-Malus und Konkurrenzabstand fließen in die Berechnung ein.
- Einzelne Beleggruppen können keine überhöhte Sicherheit erzeugen.
- Kritische Fingerprint- oder Identitätskonflikte begrenzen das Vertrauen strikt.
- Kandidaten erhalten die Stufen `candidate`, `possible`, `probable` und `confirmed_ready`.
- Die Engine trifft weiterhin keine endgültige Identitätsentscheidung.

## 2.2.2 – Semantic Identity Contradiction Detector

- Widersprüchliche Titel, Jahre, Medientypen sowie Staffel- und Episodenangaben werden erkannt.
- Fingerprint-Konflikte erhalten eine besonders hohe Priorität.
- Konflikte werden nach `low`, `medium`, `high` und `critical` eingestuft.
- Jeder Kandidat erhält eine nachvollziehbare Konfliktliste und einen vorläufigen Malus.
- Nahezu gleich starke, aber deutlich unterschiedliche Kandidaten werden als konkurrierende Hypothesen markiert.
- Die Engine trifft weiterhin keine endgültige Identitätsentscheidung.

## 2.2.1 – Semantic Identity Evidence Collector

- Kandidatenbelege werden pro Quelle und unabhängiger Beleggruppe gewichtet.
- Doppelte identische Belege werden entfernt.
- Wiederholte Treffer derselben Beleggruppe erhöhen die Sicherheit nicht künstlich.
- Pro unabhängiger Gruppe wird der stärkste Beleg für die kombinierte Stärke verwendet.
- Jeder Kandidat erhält eine nachvollziehbare Evidence Summary mit vorhandenen und fehlenden Beleggruppen.
- Einzelbelege bleiben bewusst vorsichtig bewertet.
- Die Engine trifft weiterhin keine endgültige Identitätsentscheidung.

## 2.2.0 – Semantic Identity Candidate Builder

- Neue generische Semantic-Identity-Schicht für Filme, Serien, Episoden, Hörbücher und weitere Medientypen.
- Kandidaten werden aus Dateiname, Online-Ergebnissen, OCR-/Titelkarten, lokalen Fingerprint-Treffern und bestätigtem Wissen gesammelt.
- Gleichartige Kandidaten werden normalisiert zusammengeführt.
- Belege behalten Quelle, Vertrauenswert und unabhängige Beleggruppe.
- Ein vorsichtiger Candidate Score priorisiert Kandidaten, trifft aber ausdrücklich noch keine endgültige Entscheidung.
- Die bisherige Decision Engine bleibt unverändert aktiv.

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

