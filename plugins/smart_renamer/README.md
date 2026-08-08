# MediaHub Smart Renamer

**Version:** 0.4.6

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
