## v0.4.6

- Sortierte Erkennungskandidaten mit Confidence-Ranking ergänzt.
- Confidence-Bänder `high`, `medium` und `low` eingeführt.
- Unsichere bzw. eng beieinanderliegende Ergebnisse werden mit
  `review_required` markiert.
- Gründe/Evidenz werden pro Kandidat nachvollziehbar gespeichert.
- Lokale Fallback-Kandidaten für unklare Video- und Audiofälle ergänzt.
- Provider-Vertrag für spätere KI-, Online-, MediaHub-Datenbank- und
  AI-Node-Kandidaten eingeführt.
- Externe Provider können die lokale Erkennung ergänzen, ohne sie zu ersetzen.
- Manuelle Metadaten behalten weiterhin Vorrang.
- Echte Umbenennung bleibt gesperrt.

## v0.4.5

- Konservative lokale Medienerkennung als neue Scanner-Stufe ergänzt.
- Filme, Serien, Hörbücher und Musik werden aus Dateiname, Pfad und Endung klassifiziert.
- Serienmuster `SxxExx`, `x`-Notation und deutschsprachige Staffel-/Folge-Angaben ergänzt.
- Jahr, Episodentitel und typische Schnittfassungen/Editionen werden erkannt.
- Gemischte Scan-Gruppen werden als `mixed` markiert.
- Manuell bzw. extern gelieferte Metadaten behalten immer Vorrang.
- Erkennungsdaten und Vertrauenswert werden im MediaModel gespeichert.
- Schema-Platzhalter `[edition]`, `[fassung]` und `[medientyp]` ergänzt.
- Echte Umbenennung bleibt weiterhin gesperrt.

## v0.4.4

- Web- und Mobile-OberflÃ¤che wieder funktionsfÃ¤hig.
- BeschÃ¤digten JavaScript-Zeilentrenner in der Pfadverarbeitung repariert.
- Profil- und Backend-Initialisierung startet wieder korrekt.
- Regressionstest fÃ¼r den ausgelieferten JavaScript-Code ergÃ¤nzt.
- Reine Vorschau bleibt erhalten; echte Umbenennung bleibt weiterhin gesperrt.
# Changelog

## 0.4.3

- Leeres Profilfeld in WebRemote und Mobile korrigiert.
- Eingebettete Profile werden direkt aus einer globalen JavaScript-Variable gelesen.
- Fehleranfälliges Überschreiben von `window.fetch` entfernt.
- Profil-API bleibt als Rückfallweg mit deaktiviertem Cache erhalten.
- Layout und CSS unverändert beibehalten.

## 0.4.2

- Beschädigtes Web-/Mobile-Layout aus v0.4.1 vollständig zurückgesetzt.
- Bewährte v0.4.0-HTML- und CSS-Struktur wiederhergestellt.
- Profile werden ausschließlich serverseitig abgesichert.
- Keine Änderungen mehr an responsivem Layout, CSS-Pfad oder Vorschau-JavaScript.
- Echte Umbenennung bleibt gesperrt.

## 0.4.0

- Gemeinsame Desktop-, WebRemote- und Mobile-Arbeitsoberfläche ergänzt.
- Profilwahl, Regelstapel und dynamischer Eigenschaften-Editor ergänzt.
- Regelquellen sichtbar gemacht.
- Live-Vorschau und Statusleiste ergänzt.
- Responsive Mobile-Darstellung ergänzt.
- Echte Umbenennung bleibt gesperrt.

## 0.3.1

- Gemeinsames MediaModel eingeführt.
- PreviewModel mit Info-, Warnungs-, Fehler- und Blockierungsstufen ergänzt.
- MediaScanner, Konfliktservice und RenamePipeline hinzugefügt.
- Profile für Standard, Plex, Jellyfin, Emby, Kodi und Hörbuch ergänzt.
- Lokale Grundlage für lernende Regeln ergänzt; automatische Anwendung bleibt deaktiviert.
- Web-API um Profile und Lernvorschläge erweitert.
- Echte Umbenennung bleibt gesperrt.

## 0.3.0

- Zentrale Regel-Engine ergänzt.
- Ordnerinhalt wird rekursiv für die Vorschau eingelesen.
- Regeln für Entfernen, Schreibweise, Nummerierung und Namensschema ergänzt.
- Dateiendungsschutz und Platzhalter unterstützt.
- Quellenangabe und Warnungen je Änderung ergänzt.
- Ungültige Windows-Zeichen und leere Zielnamen werden erkannt.
- Desktop- und Weboberfläche erweitert.
- Echte Ausführung bleibt gesperrt.

## 0.2.2

- Automatische ReNamer-Installation beim Installieren des Plugins ergänzt.
- Sichtbare Nicht-kommerziell-Bestätigung für ReNamer Lite ergänzt.
- Zustimmung wird in MediaHub gespeichert und nicht bei jedem Start erneut verlangt.
- Vom Benutzer bereitgestellte `Settings.ini` wird bei frischer Installation automatisch übernommen.
- ReNamer-Presets-Ordner wird automatisch vorbereitet.
- ReNamer als bevorzugtes Backend und native Engine als Fallback hinterlegt.
- Backend-Status um Priorität, Tool-ID, Lizenz, Homepage und Brückenstatus erweitert.
- Sichere Vorschau bleibt bis zur Freigabe der ReNamer-Brücke auf der nativen Engine.

## 0.2.0

- Desktop-GUI ergänzt.
- Responsive Web-/Mobile-Oberfläche ergänzt.
- Plugin-Oberflächen-Registrierung aktiviert.
- ReNamer-Erkennung auf zentralen MediaHub-Toolordner umgestellt.
- Linux-/Pi-Backend aus dem Windows-Plugin entfernt.
- Dateiendungen werden bei Regeln erhalten.
- Echte Umbenennung bleibt gesperrt.

