# MediaHub Plugins v0.5.16 – vollständiges Release

## MediaHub KI-Assistent v7.0.10

- Echte Speech-to-Text-Evidenz kann über den gemeinsamen Node-Worker-Provider auf geeigneten Windows-Compute- oder Raspberry-Pi-AI-Nodes ausgeführt werden.
- Remote Speech-to-Text besitzt weiterhin einen lokalen Fallback; nicht verfügbare Backends werden sauber gemeldet.
- Unbrauchbare kompakte Dateinamen wie `6n76g68r` werden vom zentralen Input-Quality-Gate verworfen und erzwingen bei Bedarf eine In-Video-/Speech-Verifikation.
- Ein Analyse-Cache ohne abgeschlossene In-Video-Analyse wird bei `require_in_video=True` nicht mehr fälschlich wiederverwendet.
- Der Provider-Cache verwendet einen zentralen MediaHub-Laufzeitpfad unter `plugin_data`, statt Cache-Dateien innerhalb des installierten Plugin-Verzeichnisses anzulegen.
- Speech-Evidenz kann einen erneuten Quellen- und Suchplan auslösen; klare gesprochene Akronyme wie `NCIS` werden gegenüber schwachen OCR- oder Dateinamenfragmenten priorisiert.
- Der `EpisodeIdentityResolver` kann bei starker Speech-Evidenz einen explorativen Serienabgleich starten, ohne vorher fälschlich auf einem Film-Medientyp festzuhängen.
- Eine bestätigte Episodenidentität mit `decision_authority=True` besitzt Vorrang vor älteren falschen Film-, Integration- oder Semantic-Treffern.
- Die finale Decision Engine übernimmt bei bestätigten Episoden korrekt den Medientyp `series`, Staffel und Episode, während Serien- und Episodentitel getrennt erhalten bleiben.
- Der Metadata-Review übernimmt bestätigte Serienidentitäten jetzt vollständig: Serie, Staffel, Episode und Episodentitel werden nicht mehr durch ältere Batch- oder Dateinamendaten überschrieben.
- Alte widersprüchliche Film-Cover, Beschreibungen und Veröffentlichungsdaten werden bei einer bestätigten Serienepisode nicht mehr als Fallback verwendet.
- Ein bereits vorhandener lokaler oder bestätigter Episodentitel bleibt maßgeblich, während der Online-Resolver trotzdem zur Metadaten-Anreicherung ausgeführt wird.
- Der EpisodeTitleResolver reicht Online-Zusatzdaten wie Episodenbeschreibung, Air-Date und Bildvorschlag an den Metadata-Review weiter.
- Die bereits verifizierte Serienidentität wird vor dem Batch-/Online-Schritt in das Batch-Item übernommen, sodass die Episoden-Anreicherung tatsächlich als Serie ausgeführt wird.
- TMDb und TheTVDB bestätigen den anonymisierten Test `6n76g68r.avi` gemeinsam als `NCIS`, Staffel 8, Episode 3 `Rache ist bitter`.
- Für den NCIS-Test werden zusätzlich die deutsche Episodenbeschreibung, das Ausstrahlungsdatum `2010-10-05` und ein passendes NCIS-Cover geliefert.
- Der vollständige Metadata-Editor-Test zeigt nun `series`, `NCIS`, Staffel 8, Episode 3, `Rache ist bitter`, korrekte Beschreibung, Datum und Cover mit rund 98 % Confidence.
- Die relevanten Regressionstests für Batch-Online-Enrichment und Episode-Decision laufen mit 9/9 Tests erfolgreich.

## MediaHub Audio Metadata Editor v0.0.1

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Metadata Editor v0.4.4

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Smart Renamer v0.5.17

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub AI Test Provider v1.0.0

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Speech-to-Text v0.1.2

- Unveränderter Plugin-Stand in diesem Release.
- Gemeinsames `.mhaiplugin` für Windows Compute Node und Raspberry-Pi-/Linux-AI-Node bleibt erhalten.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.
