# MediaHub Smart Renamer

**Version:** 0.4.3

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
