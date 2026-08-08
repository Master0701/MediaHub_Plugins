## v0.5.5

- Media File Grouping eingeführt.
- IDX/SUB/SRT/ASS/SSA/SUP/VTT werden unter passenden Videos gruppiert.
- SFV/MD5/SHA-Prüfsummen werden als Begleitdateien geführt.
- NFO/XML/JSON-Metadaten können dem Medienobjekt zugeordnet werden.
- Poster/Fanart/Thumb/Logo/Bilder werden gruppiert.
- Subtitle-Sprache, Forced und SDH/HI werden soweit möglich erkannt.
- Episode-Key-Gruppierung unterstützt auch reale Release-Namen wie S01E01rr.
- Nicht sicher zuordenbare Begleitdateien bleiben sichtbar.
- Begleitdateien verfälschen Sammlungstyp und Staffelzählung nicht mehr.

## v0.5.4

- Ordnerstruktur- und Sammlungsanalyse ergänzt.
- Staffelordner `Staffel`, `Season` und `Sxx` erkannt.
- Extra-/Bonus-/Trailer-/Special-Ordner erkannt.
- CD/Disc/Disk/Part/Teil-Unterordner als Part-Kontext erkannt.
- Sammlungstyp und Sammlungstitel pro Scan-Root ermittelt.
- `folder_context` und `folder_relation` pro MediaItem gespeichert.
- Fehlende Staffel-/Part-Werte können aus Ordnerstruktur ergänzt werden.
- Explizite Metadaten und sichere Einzeldateierkennung behalten Vorrang.
- Grundlage für echten Ordner-Praxistest geschaffen.

## v0.5.3

- Mehrfachfolgen-Erkennung für mehrere verbreitete Namensmuster ergänzt.
- Episode-only-Erkennung für Folge/Episode/Ep/E-Muster ergänzt.
- Specials über Staffel 0 gekennzeichnet.
- Trailer/Bonus/Extras/Deleted Scenes/Behind the Scenes/Interview/Making Of als Extras erkannt.
- Final Cut und IMAX als Editions ergänzt.
- Part/Teil/CD/Disc/Disk-Erkennung ergänzt.
- Römische Teilnummern am Filmtitel ergänzt.
- MediaItem um episode_end, part und Extra-/Special-Felder erweitert.
- Neue Schema-Platzhalter für episode_bis, teil/part und extra_type.
- Erkennung bleibt vollständig lokal und KI-unabhängig.

## v0.5.2

- Erste echte, bestätigungspflichtige Rename-Transaktion freigeschaltet.
- Planhash wird vor jeder Bestätigung/Ausführung erneut geprüft.
- Confirmation Token ist an Plan-ID + Planhash gebunden und nur einmal nutzbar.
- Dateisystem-Preflight unmittelbar vor Commit ergänzt.
- Vorhandene Ziele und doppelte Zielpfade werden strikt abgewiesen.
- v0.5.2 beschränkt echte Renames bewusst auf denselben Ordner.
- Persistentes Transaktionsjournal ergänzt.
- Automatischer Rollback bereits ausgeführter Schritte bei Folgefehlern.
- Manueller Undo/Rollback für erfolgreich abgeschlossene Transaktionen ergänzt.
- Direkte Web-/Mobile-Ausführung bleibt weiterhin gesperrt.
- Keine stille oder automatische Ausführung ohne ausdrückliche Bestätigung.

## v0.5.1

- Rename-Plan direkt in der gemeinsamen Desktop/Web/Mobile-Oberfläche sichtbar gemacht.
- Planstatus, Plan-ID, Planhash, Änderungen, Warnungen und Blockierungen ergänzt.
- Bestätigungsstatus und gesperrter Ausführungsstatus sichtbar gemacht.
- Rollback-Vorbereitung nur für technisch freigabefähige Pläne aktivierbar.
- Plan- und Rollback-Vorbereitung über bestehende sichere APIs angebunden.
- Responsive Plananzeige ergänzt.
- Oberfläche besitzt weiterhin keinen Execute-Aufruf.
- Echte Dateisystem-Umbenennung bleibt gesperrt.

## v0.5.0

- Sicheren Rename-Plan als feste Grenze zwischen Vorschau und Ausführung ergänzt.
- Plan-ID und SHA-256-Integritätshash eingeführt.
- Blockierende Konflikte verhindern die Freigabe eines Plans.
- Unsichere Decision-Ergebnisse (`review_required`) verhindern die Freigabe.
- Explizites Bestätigungs-Gate mit Confirmation Receipt vorbereitet.
- Rollback-Manifest mit Quell-/Zielpfaden und Dateizustand vorbereitet.
- Plan und `rollback.json` können im Konfigurationsbereich gespeichert werden.
- Transaktionsstatus- und Plan-API für Desktop/Web vorbereitet.
- Medien-Dateien und -Ordner werden in v0.5.0 weiterhin nicht verändert.
- `execute_rename()` und Transaktions-Commit bleiben ausdrücklich gesperrt.

## v0.4.9

- Learning Store mit Decision Engine verbunden.
- Bestätigte Medienentscheidungen werden lokal als Ranking-Hinweise gespeichert.
- Konservativer Fingerprint verhindert ungefragte Übertragung auf andere Titel.
- Lernhinweise können bevorzugten Kandidaten, Medientyp und Titel signalisieren.
- Manuelle Aufruf-Hinweise überschreiben gespeicherte Lernhinweise.
- Entscheidungshistorie kann angezeigt und gelöscht werden.
- Web/API-Hook zum Speichern bestätigter Entscheidungen ergänzt.
- Bestehendes Korrekturlernen bleibt vollständig kompatibel.
- Learning-Schema 2 mit sicherer Migration aus Schema 1 eingeführt.
- Lernen beeinflusst nur die Vorschau; echte Umbenennung bleibt gesperrt.

## v0.4.8

- Konservative Decision Engine für Erkennungskandidaten ergänzt.
- Kandidaten werden nach Confidence, Quelle und optionalen Hinweisen gerankt.
- Unbekannte Medientypen erhalten einen Sicherheitsabschlag.
- Zu unsichere oder eng beieinanderliegende Treffer erzwingen Review.
- Decision Score, Ranking und Gründe werden im Erkennungsmodell gespeichert.
- Optionale `decision_hints` für spätere Learning-/KI-/Datenbank-Signale ergänzt.
- Explizite Benutzermetadaten behalten immer Vorrang.
- Decision Engine entscheidet nur für die Vorschau; Auto-Rename bleibt gesperrt.
- Engine bleibt plugin-lokal, damit Smart Renamer weiterhin vollständig
  eigenständig läuft.

## v0.4.7

- Vollständig optionale Metadata-Editor-Integration vorbereitet.
- Capability-basierte Provider-Auflösung ergänzt.
- Smart Renamer bleibt ohne Metadata Editor vollständig eigenständig.
- Optionaler Provider kann Metadaten in die Vorschau einbringen.
- Manuelle/aufrufseitige Metadaten haben weiterhin Vorrang.
- Provider-Fehler fallen sicher auf die interne Vorschau zurück.
- Neuer Integrationsstatus für Desktop/Web/API ergänzt.
- Keine Pflichtabhängigkeit und keine automatische Installation anderer Plugins.
- Echte Umbenennung bleibt gesperrt.

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

