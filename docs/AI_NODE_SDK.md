# MediaHub AI-Node SDK

## Zweck

`shared/ai_node_sdk/` definiert gemeinsame Datenmodelle und Laufzeitverträge
für Plugins unter `ai_node_plugins/`.

Die bestehenden MediaHub-Plugins unter `plugins/` werden dadurch nicht
verändert.

## Quelle der Wahrheit

Die tatsächlichen Fähigkeiten eines AI-Node-Plugins stehen weiterhin
ausschließlich in dessen `plugin.json`, zum Beispiel:

```json
"capabilities": [
  "health_check",
  "test_provider"
]
```

Das SDK führt keine zweite Capability-Liste ein. `PluginManifest` liest die
bestehenden Manifestdaten lediglich in ein einheitliches Modell ein.

Dasselbe gilt für:

- `permissions`
- `dependencies`
- `required_tools`
- `type`
- `api_version`

## SDK 1.0.0

Die erste Version stellt bereit:

- Manifest-Lader und Manifestmodell
- Capability-Modell
- Health-Modell
- generische TaskRequest-/TaskResult-Modelle
- optionale Laufzeit-Protokolle für `health()` und `execute()`
- API-Kompatibilitätsprüfung

Plugins müssen nicht von einer SDK-Basisklasse erben. Bestehende AI-Node-
Plugins bleiben deshalb kompatibel. Neue Plugins können die gemeinsamen
Modelle und Protokolle schrittweise verwenden.
