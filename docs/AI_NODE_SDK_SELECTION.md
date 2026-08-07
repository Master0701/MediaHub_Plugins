# AI-Node SDK – Auswahl, Prioritäten und Fallback

Phase 7 ergänzt die Auswahl zwischen mehreren gleichzeitig nutzbaren Plugins.

## Keine neue Capability-Wahrheit

Capabilities bleiben ausschließlich im jeweiligen `plugin.json`.

Die neue `SelectionPolicy` gehört zur Laufzeitentscheidung des Orchestrators
und speichert keine Fähigkeiten. Sie kann lediglich festlegen:

- explizit bevorzugte Plugin-IDs,
- Laufzeit-Prioritäten,
- ob bei einem Ausführungsfehler ein Fallback erlaubt ist.

## Auswahlreihenfolge

Ein Plugin kommt nur in Betracht, wenn Phase 6 es als nutzbar bewertet:

- installiert,
- aktiviert,
- erreichbar,
- gesund,
- plattformkompatibel,
- alle `required_tools` vorhanden.

Danach sortiert Phase 7 die verbleibenden Kandidaten nach:

1. höherer Laufzeit-Priorität,
2. expliziter Bevorzugung,
3. stabiler Plugin-ID-Reihenfolge.

Schlägt die Ausführung fehl und Fallback ist erlaubt, wird der nächste
geeignete Kandidat probiert.

## Späterer Orchestrator

Der zentrale MediaHub-Orchestrator kann diese Policy dynamisch aus
Performance, Knotenwahl, Benutzerpräferenzen oder Backend-Kosten erzeugen.
Das SDK bleibt dabei nur die gemeinsame Ausführungs- und Auswahlbasis.
