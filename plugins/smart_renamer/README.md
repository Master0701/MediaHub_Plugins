# MediaHub Smart Renamer

**Version:** 0.5.16

- sichere Vorschau ohne Dateiveränderung
- Dateien und Ordner einlesen
- Regelketten: Ersetzen, Entfernen, Präfix, Suffix, Leerzeichen, Schreibweise, Nummerierung und Namensschema
- Platzhalter: `[titel]`, `[jahr]`, `[staffel]`, `[episode]`, `[episodentitel]`, `[nummer]`, `[original]`, `[endung]`
- Dateiendungen standardmäßig geschützt
- Quellenangabe und Warnungen je Vorschauzeile
- doppelte Zielnamen und ungültige Windows-Zeichen werden erkannt
- ReNamer bleibt bevorzugtes externes Backend; die sichere Vorschau läuft weiterhin nativ
- echte Umbenennung weiterhin gesperrt

## Architektur v0.3.1

- MediaModel für gemeinsame Mediendaten
- PreviewModel mit Konfliktstufen
- Scanner → Backend → Konfliktprüfung → Vorschau-Pipeline
- Profile für Standard, Plex, Jellyfin, Emby, Kodi und Hörbuch
- lokale Lernhistorie ohne automatische Anwendung

## Oberfläche v0.4.0

- dreispaltige Desktop-Arbeitsfläche
- responsive WebRemote- und Mobile-Ansicht
- Profilwahl, Regelstapel und Live-Vorschau
- Regelquellen: Benutzer, Profil, KI, ReNamer und Plugin
- Ausführung weiterhin gesperrt

## Web-/Mobile-Hotfix v0.4.2

- Die funktionierende v0.4.0-Oberfläche und ihre CSS-Route wurden vollständig wiederhergestellt.
- Profile werden serverseitig in die Seite eingebettet.
- Der bestehende Profilabruf wird lokal beantwortet, ohne HTML-, CSS- oder Layoutumbau.
- Desktop, Vorschau und übrige API-Routen bleiben unverändert.

## Direkte Profilübergabe v0.4.3

- Profile werden direkt aus `window.__SMART_RENAMER_PROFILES__` gelesen.
- Kein Überschreiben von `window.fetch` mehr.
- Profil-API bleibt nur als Rückfallweg erhalten.
- Layout und CSS bleiben unverändert.

## Lokale Medienerkennung v0.4.5

- Serienmuster wie `S02E03`, `2x03` sowie `Staffel 2 Folge 3`
- Film-Erkennung über Videoformat und Jahreszahl
- Hörbuch-Erkennung über M4B/AA/AAX sowie eindeutige Hörbuch-/Kapitelhinweise
- Musik-Erkennung für Audioformate und nummerierte Tracks
- Editions-Erkennung, unter anderem Director's Cut, Extended, Theatrical, Uncut und Remastered
- gemischte Scan-Gruppen werden als `mixed` gekennzeichnet
- vorhandene/manuell gelieferte Metadaten haben immer Vorrang vor der lokalen Erkennung
- neue Schema-Platzhalter: `[edition]`, `[fassung]`, `[medientyp]`
- weiterhin reine Vorschau; echte Umbenennung bleibt gesperrt


## Erkennungskandidaten v0.4.6

Die lokale Medienerkennung liefert jetzt nicht nur einen einzelnen Wert,
sondern eine sortierte Kandidatenliste mit Confidence-Bewertung.

- `high`, `medium` und `low` Confidence-Bänder
- `review_required` bei unsicheren oder zu nah beieinanderliegenden Treffern
- nachvollziehbare Gründe pro Kandidat
- lokale Primär- und Fallback-Kandidaten
- keine erfundenen Online-Treffer: externe Treffer kommen erst über Provider
- Provider-Vertrag für spätere MediaHub-KI-, Online-, Datenbank- oder
  AI-Node-Erkennung
- externe Provider ergänzen die lokale Erkennung, sie ersetzen sie nicht
- explizit/manuell gelieferte Metadaten haben weiterhin Vorrang
- echte Umbenennung bleibt weiterhin gesperrt


## Optionale Metadata-Editor-Integration v0.4.7

Der Smart Renamer bleibt vollständig allein lauffähig.

Wenn MediaHub zur Laufzeit eine passende Metadaten-Capability bereitstellt,
kann der Smart Renamer zusätzliche Metadaten für seine Vorschau übernehmen.
Fehlt der Metadata Editor, ist er deaktiviert oder bietet er die Capability
nicht an, verwendet der Renamer automatisch seine eigene interne Vorschau.

Grundregeln:

- keine Pflichtabhängigkeit zum Metadata Editor
- keine Änderung an MediaHub erforderlich
- keine automatische Plugin-Installation
- explizite/manuelle Renamer-Metadaten haben immer Vorrang
- Fehler eines optionalen Providers dürfen den Renamer nicht stoppen
- Web-/Status-API zeigt, ob die Integration tatsächlich aktiv ist
- echte Umbenennung bleibt weiterhin gesperrt


## Decision Engine v0.4.8

Die Kandidaten aus v0.4.6 werden jetzt durch eine konservative
Entscheidungsschicht bewertet.

Die Decision Engine:

- wählt den besten Kandidaten ausschließlich für die Vorschau,
- berücksichtigt Confidence, Quellengewicht und optionale Hinweise,
- bestraft unbekannte Medientypen,
- fordert bei zu niedriger Sicherheit oder knappen Treffern manuelle Prüfung,
- speichert Ranking, Gründe und Entscheidungsscore im MediaModel,
- akzeptiert optionale `decision_hints` für spätere Lern-/KI-/Datenbank-Hinweise,
- überschreibt niemals explizit vom Benutzer gelieferte Metadaten,
- löst niemals automatisch eine echte Umbenennung aus.

Die Decision Engine liegt bewusst zunächst im Smart-Renamer-Plugin selbst.
Damit bleibt das Plugin vollständig eigenständig. Der Datenvertrag ist so
gehalten, dass er später auch von weiteren MediaHub-Komponenten verwendet
werden kann, ohne dass der Smart Renamer von diesen abhängig wird.


## Learning + Decision Engine v0.4.9

Bestätigte Benutzerentscheidungen können jetzt lokal gespeichert und beim
nächsten Scan als vorsichtige Ranking-Hinweise an die Decision Engine
weitergegeben werden.

Sicherheitsregeln:

- Lernen erfolgt nur nach ausdrücklich bestätigter Benutzerentscheidung.
- Gelernte Werte beeinflussen ausschließlich das Ranking der Vorschau.
- Keine gelernte Regel löst eine automatische Umbenennung aus.
- Entscheidungen werden konservativ nur für denselben normalisierten
  Dateistamm und dieselbe Dateiendung wiederverwendet.
- Aufrufseitige/manuelle `decision_hints` haben Vorrang vor gespeicherten
  Lernhinweisen.
- Gelernte Entscheidungen können angezeigt und wieder gelöscht werden.
- Das bisherige Korrekturlernen (`original` → `corrected`) bleibt kompatibel.
- Schema-1-Lerndaten werden beim nächsten Speichern verlustfrei in Schema 2
  überführt.


## Sicherer Ausführungsplan v0.5.0

v0.5.0 führt noch keine echte Dateisystem-Umbenennung aus. Stattdessen wird
die vollständige Sicherheitsstrecke bis unmittelbar vor den späteren Commit
aufgebaut.

Enthalten:

- unveränderlicher Rename-Plan aus der aktuellen Vorschau
- eindeutige Plan-ID
- SHA-256-Integritätshash über relevante Planinhalte
- Konflikt-Gate: blockierende Preview-Probleme verhindern Freigabe
- Review-Gate: unsichere Decision-Ergebnisse verhindern Freigabe
- Status `awaiting_confirmation` nur bei konfliktfreiem, eindeutigem Plan
- explizite Benutzerbestätigung als separater Schritt
- Bestätigungs-Receipt/Token ohne Freischaltung einer Ausführung
- vorbereitete `rollback.json` mit alten und geplanten neuen Pfaden
- optionales Speichern von `rename_plan.json` + `rollback.json` ausschließlich
  im MediaHub-Konfigurationsbereich
- keine Medien-Datei oder kein Medien-Ordner wird dabei verändert
- `execute_rename()` und der Transaktions-Commit bleiben weiterhin gesperrt

Damit ist Vorschau → Plan → Konfliktprüfung → Bestätigung → Rollback-
Vorbereitung vorhanden, während die tatsächliche Rename-Engine noch nicht
freigeschaltet wird.


## Plan- und Rollback-Oberfläche v0.5.1

Die gemeinsame Desktop-/WebRemote-/Mobile-Oberfläche zeigt jetzt den in
v0.5.0 eingeführten Sicherheitsplan sichtbar an.

- eigener Button `Rename-Plan`
- Planstatus, Plan-ID und SHA-256-Planhash
- Anzahl Änderungen, Warnungen und blockierende Konflikte
- sichtbarer Hinweis auf erforderliche Bestätigung
- sichtbarer Status `Ausführung gesperrt`
- `Rollback vorbereiten` wird nur bei technisch freigabefähigem Plan aktiv
- Vorbereitung speichert ausschließlich Plan-/Rollback-Daten im
  Konfigurationsbereich
- kein Execute-Endpunkt wird von der Oberfläche aufgerufen
- responsive Darstellung für Mobile Dashboard/WebRemote
- Smart Renamer bleibt ohne andere Plugins vollständig nutzbar

Die echte Rename-Transaktion bleibt weiterhin deaktiviert.


## Transaktionale Rename Engine v0.5.2

v0.5.2 schaltet die erste echte Dateisystem-Umbenennung frei, jedoch nur über
den bestätigungspflichtigen Transaktionspfad.

Sicherheitsbedingungen:

- ausführbarer, konfliktfreier Rename-Plan erforderlich
- Planhash wird unmittelbar vor der Transaktion erneut geprüft
- Bestätigung muss ausdrücklich für exakt diesen Plan erzeugt worden sein
- Bestätigungstoken ist nur einmal verwendbar
- Quellen und Ziele werden direkt vor dem Commit erneut geprüft
- vorhandene Ziele werden niemals überschrieben
- doppelte Zielpfade werden abgewiesen
- v0.5.2 erlaubt bewusst nur Rename innerhalb desselben Ordners
- jeder ausgeführte Schritt wird im Journal protokolliert
- schlägt ein späterer Schritt fehl, werden bereits erfolgte Renames
  automatisch in umgekehrter Reihenfolge zurückgerollt
- eine erfolgreich abgeschlossene Transaktion kann manuell per Undo/Rollback
  zurückgenommen werden
- direkte Web-/Mobile-Ausführung bleibt in v0.5.2 noch gesperrt; dort werden
  weiterhin nur Vorschau, Plan und Rollback-Vorbereitung angeboten

Damit kann die Rename Engine erstmals echte Änderungen durchführen, aber nur
über die explizit bestätigte Python/Host-Schnittstelle. Die sichtbare
Bestätigungs-/Execute-Oberfläche folgt getrennt, damit keine Remote- oder
UI-Ausführung versehentlich freigeschaltet wird.


## Erweiterte Serien-/Filmerkennung v0.5.3

Neu erkannt werden unter anderem:

- Mehrfachfolgen wie `S01E01-E02`, `S01E01E02` und `2x03-04`
- einzelne Episodenangaben wie `Folge 12` oder `Ep05`
- Specials über Staffel 0 / `S00`
- Trailer, Bonus, Extras, Deleted Scenes, Behind the Scenes, Interviews und Making Of
- weitere Editionen wie `Final Cut` und `IMAX`
- Teile/Discs wie `Part 2`, `Teil 2`, `CD2`, `Disc 2`
- einfache römische Teilnummern am Filmtitel, z. B. `Rocky II`
- neue strukturierte Felder `episode_end`, `part`, `extra_type`,
  `is_special`, `is_extra`, `is_bonus`
- zusätzliche Schema-Platzhalter `[episode_bis]`, `[teil]`, `[part]`, `[extra_type]`

Diese lokale Erkennung bleibt vollständig ohne MediaHub-KI lauffähig. Ist die
KI später vorhanden, kann sie schwierige oder unklare Fälle ergänzen.


## Ordnerstruktur- und Sammlungsanalyse v0.5.4

Der Scanner betrachtet jetzt nicht mehr nur einzelne Dateien, sondern ergänzt
bei Verzeichnis-Scans einen gemeinsamen Ordnerkontext.

Erkannt werden unter anderem:

- Serien-/Sammlungsname aus dem Scan-Root
- Staffelordner wie `Staffel 01`, `Season 2`, `S03`
- Extra-/Bonus-/Trailer-/Special-Ordner
- CD/Disc/Disk/Part/Teil-Unterordner
- dominante Sammlungsklasse (`series`, `movie`, `music`, `audiobook`, `mixed`)
- Beziehungen jeder Datei zu ihrem übergeordneten Ordner
- Season-/Part-Werte aus Ordnern, wenn sie im Dateinamen fehlen
- strukturierter `folder_context` und `folder_relation` im MediaItem

Explizite/manuelle Metadaten und sichere Einzeldateierkennung behalten immer
Vorrang. Die Ordneranalyse ergänzt nur fehlende Informationen.

Damit ist die Grundlage für den ersten großen Praxistest mit echten
Medienordnern vorbereitet.


## Media File Grouping v0.5.5

Begleitdateien werden jetzt nicht mehr als eigene Medienobjekte behandelt,
wenn ein passendes Video gefunden wird.

Gruppiert werden unter anderem:

- Untertitel: SRT, ASS, SSA, SUB, IDX, SUP, VTT
- Metadaten: NFO, XML, JSON
- Bilder: Poster, Fanart, Thumb, Logo und allgemeine Bilder
- Prüfsummen: SFV, MD5, SHA1, SHA256
- Text-/Begleitdateien
- Playlist-/Cue-Dateien

Untertitelinformationen wie Sprache, `forced` und `SDH/HI` werden soweit aus
dem Dateinamen erkennbar mitgespeichert.

Wichtig: Kann eine Begleitdatei keinem Medium sicher zugeordnet werden,
bleibt sie sichtbar und wird als `companion_unmatched` markiert. Dadurch geht
bei unsicherer Gruppierung nichts stillschweigend verloren.


## Media Relation Engine v0.5.6

Die Relation Engine führt gemeinsame, plattformneutrale Felder für komplexe
Medienbeziehungen ein. Diese Struktur ist für Smart Renamer, Metadata Editor,
MediaHub-KI-Assistent und Cut & Merge vorgesehen.

Unterstützte Relationstypen:

- `single`
- `missing_episode`
- `multi_episode`
- `split_episode`
- `split_movie`
- `multi_part`
- `duplicate_candidate`
- `sample`
- `unknown_relation`

Wichtig: Eine Lücke in der Episodennummerierung wird zunächst nur als
`missing_episode_candidates` markiert. Der Smart Renamer behauptet NICHT,
dass die Episode tatsächlich fehlt. Ob sie in einer Doppel-/Mehrfachfolge
enthalten ist, muss durch offizielle Metadaten, Benutzerentscheidung,
KI-Auswertung oder spätere In-Video-Analyse bestätigt werden.

### Namensprofile

v0.5.6 bereitet getrennte Profile für Plex, Jellyfin, Emby und Kodi vor.
Die Profile können später über die Oberfläche ausgewählt bzw. als eigenes
Benutzerprofil überschrieben werden.

Beispiele Plex:

- Mehrfachfolge: `Titel - S01E05-E06`
- Geteilte Episode: `Titel - S01E05 - pt1`
- Geteilter Film: `Titel (Jahr) - pt1`

Es wird in v0.5.6 weiterhin nichts automatisch geschnitten, zusammengefügt
oder aufgrund einer Relation ohne Bestätigung umbenannt.


## Relation Preview & Profile Selection v0.5.7

Die Media-Relation-Engine wird jetzt über eine eigene Vorschau nutzbar.

Die Vorschau zeigt unter anderem:

- erkannte Beziehung
- aktives Namensprofil
- aktuellen Dateinamen
- vorgeschlagenen profilkonformen Dateinamen
- empfohlene Aktion
- Confidence
- Review-Status
- Begründungen/Evidence
- Warnungen
- sichere Handlungsoptionen

Eingebaute Profile:

- Plex
- Jellyfin
- Emby
- Kodi

Zusätzlich können eigene Benutzerprofile gespeichert werden. Eingebaute
Profile können weder überschrieben noch gelöscht werden.

Die Vorschau führt weiterhin KEINE Umbenennung, kein Merge und keinen Split
aus. Bei Multi-Episode, Split-Episode, Split-Movie und Episodenlücken bleibt
die Benutzerprüfung erhalten.


## Interactive Preview v0.5.8

Grundlage für den ersten echten Oberflächentest: Gruppenansicht, Profilwahl,
Vorher/Nachher, Relationsstatus, Confidence, Filter, Detailansicht und reine
Vorschauentscheidungen.

Rename, Merge und Split bleiben weiterhin gesperrt.


## GUI Wiring v0.5.9

Letzter Infrastrukturstand vor dem ersten echten Oberflächentest:
Mehrfachauswahl, Sammelentscheidungen, Statusfilter, Suche/Sortierung,
manuelle Zielnamen und optionale Integrationspunkte für Metadata Editor und
MediaHub-KI-Assistent. Beide Integrationen bleiben optional.

Rename, Merge und Split bleiben gesperrt.


## GUI Parity & Layout Fix v0.5.11

- Web: native Datei- und Ordnerauswahl zusätzlich zum Pfadfeld.
- Original/Vorschlag deutlich breiter.
- Lange Namen mit vollständigem Tooltip.
- Desktop: Relation, Confidence und Review direkt in der Vorschau.
- Gemeinsame Preview-Presentation-Schicht für Desktop und Web.
- JavaScript-Assets explizit als Plugin-Routen.
- Keine Dateiänderungen; Rename/Merge/Split bleiben gesperrt.


## v0.5.11

- Web-Picker auf sichtbaren TopMost-STA-Dialog umgestellt.
- Vorschau nach links verschoben; rechter Regelbereich bleibt breiter sichtbar.
- Desktop um Suche, Statusfilter, Sortierung, Auswahlaktionen, Statistik und Details ergänzt.
- Lange Original-/Vorschlagsnamen sind zusätzlich vollständig in der Detailansicht sichtbar.
- Alle Auswahlaktionen bleiben reine Vorschau.


## v0.5.12 Review & Interactive Preview
- Verständliche Review-Gründe.
- KI-Review über optionale Capability `ai.rename_review`.
- KI bleibt optional; Benutzerbestätigung bleibt Pflicht.
- Rename/Merge/Split bleiben gesperrt.


## KI-Review-Integration v0.5.13

- `ai.rename_review` hängt jetzt an der bestehenden optionalen Capability-Verwaltung.
- `attach_optional_provider("ai.rename_review", provider)` macht einen Provider sofort nutzbar.
- Web und Desktop zeigen Providerstatus und Providernamen.
- Ein einzelner Review-Fall kann gezielt von der KI analysiert werden.
- Sichtbar sind Empfehlung, optionaler Namensvorschlag, Confidence, Begründung und Warnungen.
- Ohne Provider bleibt manueller Review vollständig erhalten.
- KI darf niemals Rename/Merge/Split ausführen.
- Benutzerbestätigung bleibt zwingend.


## Decision Fusion v0.5.14

- Renamer-Erkennung und optionale KI-Empfehlung werden getrennt bewertet.
- Stimmen beide überein, darf die Confidence moderat steigen.
- Widersprechen sie sich, bleibt der Fall zwingend auf `Bitte prüfen`.
- Ohne KI-Provider bleibt die normale Renamer-Bewertung aktiv.
- Niedrige Sicherheit bleibt ein Review-Fall.
- Web und Desktop zeigen Agreement, kombinierte Confidence und Begründung.
- Auch bei hoher Confidence gibt Decision Fusion niemals eine Dateisystem-Ausführung frei.


## Review Evidence / Decision Explanation v0.5.15

- Für einen Review-Fall werden einzelne Belege nach Quelle ausgewiesen.
- Quellen können Renamer-Erkennung, Relation/Staffel-Episode, Review-Gründe,
  Metadatenhinweise, optionale KI und Decision Fusion sein.
- Jede Quelle kann eigene Confidence und Detailbegründung anzeigen.
- Widersprüche werden ausdrücklich als Konflikte markiert.
- Web und Desktop können die Belege für genau einen ausgewählten Fall anzeigen.
- Evidence ist reine Erklärung: keine automatische Rename-/Merge-/Split-Ausführung.


## Review-Priorisierung v0.5.16

- Konflikte und blockierende Fälle stehen ganz oben.
- Split-/Multi-Episode und Split-Movie erhalten erhöhte Priorität.
- Niedrige Confidence erhöht die Review-Priorität.
- Bestehende Review-Gründe fließen in die Priorität ein.
- Web/Desktop können nach Priorität filtern und sortieren.
- Priorisierung ändert keine Entscheidung und führt niemals Dateien aus.


## v0.5.16 GUI Fix 2
Profilwechsel behält bei Serien Staffel/Episode. Zusätzlich können Titel,
Jahr, SxxExx, Episodentitel, Edition, Teil usw. in Desktop und Web frei
angeordnet werden.
