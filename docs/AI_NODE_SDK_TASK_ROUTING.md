# AI-Node SDK – Aufgaben- und Capability-Routing

Phase 5 ergänzt den gemeinsamen Laufzeitvertrag für Aufgaben.

## Grundregel

Das SDK entscheidet niemals selbst, was ein Plugin kann.

Die Quelle der Wahrheit bleibt ausschließlich:

```text
ai_node_plugins/<plugin>/plugin.json
```

und dort das vorhandene Feld:

```json
"capabilities": [...]
```

## Ablauf

1. Der Orchestrator erzeugt einen `TaskRequest`.
2. `find_candidates()` sucht ausschließlich installierte Plugins, deren
   Manifest die geforderte Capability enthält.
3. `route_task()` wählt einen passenden Kandidaten.
4. `execute_task()` blockiert jede nicht deklarierte Capability.
5. Hat ein Plugin bereits `execute()`, wird dieser gemeinsame Einstieg
   verwendet.
6. Bestehende Plugins ohne `execute()` bleiben kompatibel: Eine Capability
   kann auf eine gleichnamige vorhandene Methode zeigen.

Damit muss der aktuelle MediaHub AI Test Provider nicht geändert werden.

## Spätere Erweiterung

Der Router ist bewusst noch einfach. Der zentrale MediaHub-Orchestrator kann
später zusätzliche Informationen berücksichtigen:

- Health-Status
- Plattform
- Tool-Verfügbarkeit
- Plugin-Aktivierung
- Priorität
- Laufzeit/Performance
- lokaler PC vs. AI-Node vs. Cloud

Diese Auswahlregeln gehören in den Orchestrator und werden nicht als zweite
Capability-Liste im SDK gespeichert.
