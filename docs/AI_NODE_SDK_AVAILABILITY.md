# AI-Node SDK – Verfügbarkeit und Routing

Phase 6 ergänzt die verbindliche Laufzeitprüfung vor jeder Aufgabenvergabe.

Ein Plugin darf nur verwendet werden, wenn es:

- installiert,
- aktiviert,
- erreichbar,
- gesund,
- plattformkompatibel

ist und alle in seinem bestehenden `plugin.json` deklarierten
`required_tools` tatsächlich verfügbar sind.

Das SDK installiert niemals Tools oder Plugins stillschweigend.

Die Capability-Quelle bleibt weiterhin ausschließlich das Plugin-Manifest.
Die Runtime-Statusdaten kommen vom AI-Node bzw. vom Orchestrator und werden
nicht dauerhaft als zweite Wahrheit im SDK gespeichert.

Fehlt ein Plugin oder Tool, muss der Orchestrator einen anderen geeigneten
Knoten bzw. ein anderes Backend wählen oder die Fähigkeit als aktuell nicht
verfügbar melden.
