# MediaHub Smart Renamer

**Version:** 0.4.9

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
