# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 7.0.9**
- **MediaHub Audio Metadata Editor 0.0.1**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.4.4**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.5.17**
- **MediaHub WebRemote 0.13.7**
- **MediaHub AI Test Provider 1.0.0**
- **MediaHub Speech-to-Text 0.1.2**

# MediaHub Plugins v0.5.15 – vollständiges Release

## MediaHub KI-Assistent v7.0.9

- Echte Speech-to-Text-Evidenz kann jetzt über den gemeinsamen Node-Worker-Provider auf geeigneten Windows-Compute- oder Raspberry-Pi-AI-Nodes ausgeführt werden.
- Remote Speech-to-Text besitzt weiterhin einen lokalen Fallback; nicht verfügbare Backends werden sauber gemeldet.
- In-Video-/Speech-Evidenz löst nach der Analyse einen erneuten Quellen- und Suchplan aus, sodass erkannte Identitätshinweise tatsächlich für den Online-Abgleich verwendet werden.
- Klare gesprochene Akronyme wie NCIS werden gegenüber schwachen OCR-Fragmenten korrekt priorisiert.
- Unbrauchbare kompakte Datei-Codes wie `6n76g68r` werden durch das Identitäts-Quality-Gate verworfen und können nicht mehr als finale Medienidentität zurückkehren.
- Online- und Semantic-Evidenz können bei verworfenem Dateinamen den effektiven Titel und Medientyp übernehmen.
- TMDb-Zugangsdaten und Provider-Konfiguration verwenden auch im Entwicklungsbetrieb den echten MediaHub-Laufzeitpfad.
- TMDb kann jetzt Episodenkandidaten einer erkannten Serie inklusive Staffel, Episodennummer, Titel, Beschreibung, Airdate und Provider-ID bereitstellen.
- Neuer `EpisodeIdentityResolver`: konkrete Serienepisoden werden anhand von In-Video-/Speech-Handlungskonzepten und Beziehungen gegen Provider-Episodendaten bewertet.
- Episoden werden nur bei ausreichend hoher Evidenz und eindeutigem Abstand zum zweitbesten Kandidaten automatisch bestätigt.
- Bestätigte Episoden werden als eigene starke Evidence in die Decision Engine übernommen.
- Eine starke unabhängige Online-Serienbestätigung zusammen mit einer bestätigten In-Video-Episode kann die finale Medienidentität auf `confirmed` setzen.
- Der anonymisierte Test `6n76g68r.avi` wird vollständig als `NCIS`, Serie, Staffel 8, Episode 3 `Rache ist bitter` erkannt.
- Neue Regressionstests sichern Episode-Evidence, Medientyp, Staffel/Folge, Decision Authority und Compact-Code-Schutz ab.
- Aktueller Regressionstest dieses Erkennungswegs: 7 Tests erfolgreich.

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

- Gemeinsames `.mhaiplugin` für Windows Compute Node und Raspberry-Pi-/Linux-AI-Node bleibt erhalten.
- Windows kann bei fehlendem `py.exe` eine verwaltete private Python-Runtime für Speech-to-Text verwenden.
- Speech-Runtime wird persistent im verwalteten Node-/Plugin-Runtime-Bereich abgelegt.
- UTF-8-Ausgabe des Speech-Subprozesses wird erzwungen, sodass deutsche Sonderzeichen keine fehlerhaften JSON-/Decode-Fehler mehr verursachen.
- Unterstützt begrenzte Identitätsanalysen über `max_segments` und `max_audio_seconds`, ohne vollständige Transkriptionen unnötig auszuführen.
- Windows-Ausführung wurde sowohl per CPU als auch per CUDA/GPU erfolgreich geprüft.
- Raspberry-Pi-/Linux-Ausführung wurde erfolgreich per CPU geprüft.
- Liefert Transcript, Segmente, Sprache, Confidence, Truncation-Informationen und Ausführungsdaten für die nachgelagerte MediaHub-KI.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.

## Kompatibilität

- **MediaHub KI-Assistent 7.0.9** – mindestens MediaHub v1.0.17
- **MediaHub Audio Metadata Editor 0.0.1** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.4.4** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.5.17** – mindestens MediaHub v1.0.18
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5
- **MediaHub AI Test Provider 1.0.0** – AI-Node API 1
- **MediaHub Speech-to-Text 0.1.2** – AI-Node API 1

## Projektaufbau

- `plugins/` – MediaHub-Plugins (`.mhplugin`)
- `ai_node_plugins/` – AI-Node-/Raspberry-Pi-Plugins (`.mhaiplugin`)
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – Plugin-Store- und Updatekataloge
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `tools/dev/` – dauerhaft nützliche Entwickler- und Diagnosetools
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Release ausführen

Lokaler Prüflauf ohne Veröffentlichung:

```powershell
release_plugins.cmd -Tag v0.5.5 -NoPush
```

Vollständiges Release:

```powershell
release_plugins.cmd -Tag v0.5.5
```

Alle Versions- und Paketnamen werden automatisch aus den jeweiligen
`plugins/*/plugin.json` und `ai_node_plugins/*/plugin.json` übernommen.
