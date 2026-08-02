# MediaHub KI-Assistent v4.9.0

Der MediaHub KI-Assistent ist die zentrale lokale Orchestrierungs- und Entscheidungsinstanz für Medienanalyse, Wissensabgleich, Qualitätsbewertung und die Zusammenarbeit mit weiteren MediaHub-Plugins.

## Aktueller Funktionsumfang

### Medienanalyse und Entscheidungen

- Mehrstufige Analyse mit Supervisor-Agent und erklärbarer Decision Engine.
- Gewichtete, voneinander getrennte Beweise aus Dateiname, Online-Treffern, Untertiteln, OCR und Fingerprints.
- Widerspruchserkennung, Vertrauensstufen und klare Empfehlungen statt erzwungener Identitäten.
- Analyse-Cache mit Wiederherstellung und Neuberechnung aktueller Entscheidungsdaten.

### Such- und Quellenlogik

- Semantic Query Pipeline mit gewichteten Suchvarianten.
- Qualitätsprüfung gegen technische Tokens, schwache Einzelwörter und OCR-Zeichensalat.
- Provider-Registry, parallele Ausführung, Cache, Diagnosen und Ergebnisranking.
- TMDb-, TVDb- und Wikipedia-Provider; unbekannte Medientypen können medientypübergreifend gesucht werden.

Optional können Umgebungsvariablen gesetzt werden:

- `MEDIAHUB_TMDB_API_KEY` oder `MEDIAHUB_TMDB_BEARER_TOKEN`
- `MEDIAHUB_TVDB_API_KEY`
- `MEDIAHUB_TVDB_SUBSCRIBER_PIN` nur bei einem entsprechenden TheTVDB-Schlüssel

Wikipedia ist standardmäßig aktiviert und benötigt keinen Schlüssel.

### Wissenssystem und Lernen

- Persistenter Knowledge Graph für Filme, Serien, Staffeln, Episoden, Specials, Bücher und Hörbücher.
- Beziehungen für Franchise, Universum, Spin-off, Prequel, Sequel, Crossover, Backdoor-Pilot, Starts-in-Episode und erste Auftritte.
- Getrennte chronologische, Veröffentlichungs-, empfohlene und benutzerdefinierte Reihenfolgen.
- Bestätigtes Lernen von Identitäten, Aliasregeln, Fingerprints und visuellen Merkmalen.
- Ableitungen und Vorschläge werden nicht ohne Bestätigung dauerhaft gespeichert.
- Export-Snapshots bereiten die Übergabe an Listen & Export vor.

### In-Video- und Visual Intelligence

- Frame-, OCR-, Untertitel-, Audio-, Fingerprint- und Szenenagenten.
- Smart Frame Selection mit gezielter Verteilung auf Intro, Handlung und Outro.
- Schärfe-, Kontrast-, Schwarzbild-, Weißbild- und Duplikatfilterung.
- Perceptual Average-Hash, Difference-Hash und zentraler Motiv-Hash.
- Mehrbild-Visual-Fingerprint und normalisierte Scene Signature.
- OCR-/Logo-Fusion mit strenger Mindestqualität.
- Anonyme Gruppierung wiederkehrender Zentralmotive ohne Gesichtserkennung, biometrische Identifikation oder Namenszuordnung.
- Heuristische Intro-/Outro-Erkennung.
- Visual Knowledge nur nach bestätigter Medienidentität.
- Vollständige Pipeline-Validierung für Konsistenz, Datenschutz und Integrität.

### Datenschutz und Online Visual Provider

Die visuelle Analyse läuft standardmäßig vollständig lokal. Der optionale Visual Provider ist deaktiviert und benötigt:

1. eine explizite Konfiguration,
2. eine ausdrückliche Benutzerfreigabe,
3. eine begrenzte Auswahl einzelner Frames.

Komplette Videos und Audiospuren werden niemals über diese Schnittstelle übertragen.

### Qualität und Werkzeuge

- Technische Bild-, Ton- und Gesamtbewertung.
- Persönliche Referenzprofile und Qualitätsvergleich.
- Statusstufen von „sehr gut“ bis „neu in besserer Qualität suchen“.
- Qualitätsentscheidungen führen niemals automatisch zu Löschung oder Austausch.
- Zentrale Werkzeugerkennung für FFmpeg, FFprobe, MediaInfo, Tesseract und MKVToolNix.
- Fehlende optionale Werkzeuge deaktivieren nur die betreffende Funktion.

### Backends und Orchestrierung

- Interne MediaHub-KI als Standard- und Fallback-Backend.
- Vorbereitung für einen optionalen Raspberry-Pi-AI-Node.
- Lokaler Orchestrator mit nachvollziehbaren Teilschritten, Fähigkeiten und Werkzeuganforderungen.
- Task- und Agentenverwaltung mit Status- und Diagnoseinformationen.

### Plugin-Integration

- Stabile Übergabe-API für Metadata Editor und Smart Renamer.
- Vorbereitete Zusammenarbeit mit Listen & Export, Hörbuchverwaltung und zukünftigen Plugins.
- Desktop- und Weboberfläche mit Backend-, Werkzeug- und Capability-Status.

## Testen und Bauen

```powershell
python -m pytest plugins/ai_assistant/tests -q
python -m compileall plugins/ai_assistant
python build_plugins.py ai_assistant --clean
```

## Kompatibilität

- Plugin-Version: **4.9.0**
- Mindestens erforderlich: **MediaHub v1.0.17**
- Internetzugriff: optional
- Lokale Medien- und Wissensdaten werden nicht automatisch extern übertragen.

