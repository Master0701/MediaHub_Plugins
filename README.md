# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub KI-Assistent 4.9.0**
- **MediaHub Hörbuchverwaltung 0.0.0**
- **MediaHub Listen & Export 0.0.0**
- **MediaHub Metadata Editor 0.3.6**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub Smart Renamer 0.0.0**
- **MediaHub WebRemote 0.13.7**

# MediaHub Plugins v0.5.5 – vollständiges Release

## MediaHub WebRemote v0.13.7

- Lokale Desktop-Weboberfläche für PC und Notebook.
- Browserbasierte Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben verfügbar.
- WebRemote bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.

## MediaHub Mobile Dashboard v0.1.7

- Mobile Oberfläche für Handy und Tablet.
- Einklappbare linke Sidebar und Geräte-Kopplung bleiben verfügbar.
- Mobile Dashboard bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.

## MediaHub Metadata Editor v0.3.6

- Desktop- und Weboberfläche bleiben gemeinsam verfügbar.
- Bearbeitung von Metadaten, NFO-Dateien und Medienbildern.
- Integration als zusätzliche Oberfläche in WebRemote und Mobile Dashboard.

## MediaHub KI-Assistent v4.9.0

- Mehrstufige Medienerkennung mit Supervisor-Agent und erklärbarer Decision Engine.
- Semantic Query Pipeline mit intelligenter Suchvarianten-Erzeugung, Qualitätsprüfung und Quellenbewertung.
- Knowledge Graph mit Franchise-, Universums-, Spin-off-, Prequel-, Sequel-, Crossover-, Episoden- und Reihenfolgebeziehungen.
- Lernende Wissensdatenbank mit bestätigten Identitäten, Aliasregeln und Fingerprint-Zuordnungen.
- Analyse-Cache mit Wiederherstellung und Neuberechnung aktueller Entscheidungsdaten.
- OCR-, Audio-, Frame-, Szenen-, Untertitel- und Fingerprint-Agenten.
- Smart Frame Selection mit Schärfe-, Kontrast-, Schwarzbild- und Duplikatfilterung.
- Visual Fingerprint und Scene Signature für lokale Inhaltsvergleiche.
- OCR-/Logo-Fusion mit strenger Filterung unbrauchbarer OCR-Ergebnisse.
- Anonyme Vorbereitung wiederkehrender visueller Motive ohne biometrische Identifikation.
- Intro-/Outro-Erkennung und bestätigungsgebundenes Visual Knowledge.
- Vollständige lokale Visual-Intelligence-Pipeline mit Integritäts- und Datenschutzprüfung.
- Optionale Online-Visual-Provider-Schnittstelle, standardmäßig deaktiviert und nur nach ausdrücklicher Freigabe ausgewählter Einzelbilder.
- Lokale Qualitätsbewertung und Referenzvergleich.
- TMDb-, TVDb- und Wikipedia-Provider sowie erweiterbare Provider-Architektur.
- Übergabe-API für Metadata Editor, Smart Renamer, Listen & Export und zukünftige Plugins.
- Erfordert mindestens MediaHub v1.0.17.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Der Plugin-Katalog wurde aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben sichtbar, werden aber nicht als installierbare Release-Pakete veröffentlicht.

## Kompatibilität

- **MediaHub KI-Assistent 4.9.0** – mindestens MediaHub v1.0.17
- **MediaHub Hörbuchverwaltung 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Listen & Export 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub Metadata Editor 0.3.6** – mindestens MediaHub v1.0.5
- **MediaHub Mobile Dashboard 0.1.7** – mindestens MediaHub v1.0.5
- **MediaHub Smart Renamer 0.0.0** – mindestens MediaHub v1.0.17
- **MediaHub WebRemote 0.13.7** – mindestens MediaHub v1.0.5

## Projektaufbau

- `plugins/` – getrennte, einzeln installierbare Plugins
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – Plugin-Store- und Updatekataloge
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `tools/dev/` – dauerhaft nützliche Entwickler- und Diagnosetools
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Plugins bauen

Alle Plugins sauber neu erstellen:

```powershell
python build_plugins.py all --clean
```

Nur den KI-Assistenten erstellen:

```powershell
python build_plugins.py ai_assistant --clean
```

Die fertigen `.mhplugin`-Dateien und `.sha256`-Prüfsummen liegen anschließend unter `release/`.

## Tests

Alle Tests des KI-Assistenten ausführen:

```powershell
python -m pytest plugins/ai_assistant/tests -q
```

Python-Dateien zusätzlich kompilieren:

```powershell
python -m compileall plugins/ai_assistant
```

## Release vorbereiten

```powershell
python prepare_plugin_release.py
```

Dieser Befehl übernimmt `RELEASE_NOTES_PENDING.md` in die verfolgte Datei
`RELEASE_NOTES.md` und aktualisiert diese README. Die temporäre Pending-Datei
bleibt lokal und wird nicht in Git aufgenommen.


