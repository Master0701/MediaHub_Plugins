# MediaHub AI-Node SDK 1.0.0

Das AI-Node SDK 1.0.0 ist die gemeinsame Laufzeit- und Datenmodellbasis für
Plugins unter `ai_node_plugins/`.

## Bestehende MediaHub-Plugins

Plugins unter `plugins/` bleiben unverändert und verwenden weiterhin das
bestehende MediaHub-Plugin-System.

## Quelle der Wahrheit

Jedes AI-Node-Plugin beschreibt seine tatsächlichen Fähigkeiten weiterhin
ausschließlich im eigenen `plugin.json`.

Das SDK dupliziert keine Capability-, Tool-, Permission- oder Dependency-
Listen.

## Bestandteile von SDK 1.0.0

- Manifestmodell und Manifest-Lader
- Capability-Modell
- Plugin-Loader
- Health-Vertrag
- TaskRequest / TaskResult
- Capability-Ausführung
- Capability-Methoden-Verträge
- Verfügbarkeitsprüfung
- Aktivierungs-/Health-/Plattformprüfung
- `required_tools`-Prüfung
- Prioritäten und explizite Bevorzugung
- Fallback zwischen mehreren Plugins
- Jobmodell und thread-sichere In-Memory-Queue
- Fortschritt und Abbruchstatus
- Vorbereitung für mehrere AI-Node-Knoten
- API-/SDK-Kompatibilitätsprüfung
- vollständiger AI-Node-Plugin-Audit

## Sicherheits- und Routinggrundsatz

Ein Plugin darf nur eingesetzt werden, wenn es tatsächlich installiert,
aktiviert, erreichbar, gesund, plattformkompatibel und mit allen benötigten
Tools verfügbar ist.

Das SDK installiert niemals stillschweigend Plugins oder Zusatztools.

## API-Kompatibilität

SDK 1.0.0 unterstützt aktuell AI-Node Plugin API `1`.

Plugins mit einer nicht unterstützten `api_version` werden beim Laden bzw.
Audit abgewiesen.

## Kommandozeilen-Audit

```powershell
python .\tools\validate_ai_node_sdk.py
```

Der Audit lädt und prüft alle vorhandenen AI-Node-Plugins und beendet sich
mit Fehlercode 1, sobald ein schwerer SDK-/Pluginfehler gefunden wird.

## Nächster Entwicklungsschritt

Auf diesem Fundament können echte AI-Node-Plugins entwickelt werden, zum
Beispiel Renamer, Medienerkennung, Qualitätsanalyse, OCR, lokale
Speech-to-Text-Backends oder weitere Hintergrunddienste.
