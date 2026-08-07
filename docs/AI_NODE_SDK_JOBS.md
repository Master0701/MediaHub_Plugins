# AI-Node SDK – Jobs, Warteschlange und Fortschritt

Phase 8 ergänzt ein gemeinsames Jobmodell für längere AI-Node-Aufgaben.

## Statuswerte

- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`

Jeder Job enthält unter anderem:

- eindeutige Job-ID,
- ursprünglichen `TaskRequest`,
- Fortschritt von 0 bis 100,
- Statusmeldung,
- Node-ID,
- optionale Worker-ID,
- Ergebnis bzw. Fehler,
- Erstellungs- und Änderungszeitpunkt.

## Mehrere AI-Nodes

`claim_next(node_id=...)` reserviert einen wartenden Job atomar für genau
einen Knoten. Damit ist die Datenstruktur bereits für mehrere parallel
arbeitende AI-Nodes vorbereitet.

## Kein versteckter Hintergrunddienst

Das SDK startet selbst keine Threads, Prozesse oder Netzwerkdienste.

Der AI-Node beziehungsweise der zentrale Orchestrator entscheidet, wann ein
Worker einen Job claimt und ausführt. Das hält SDK, Dienst und Orchestrator
sauber getrennt.

## Abbruch

Ein noch wartender oder laufender Job kann auf `cancelled` gesetzt werden.
Für echte langlaufende Plugin-Prozesse muss der ausführende Worker später
zusätzlich das Abbruchsignal beachten und seine konkrete Verarbeitung
beenden.

## Persistenz

Phase 8 verwendet bewusst eine thread-sichere In-Memory-Queue. Eine
persistente Datenbank-/REST-Anbindung gehört in den AI-Node-Dienst und kann
auf demselben Jobmodell aufbauen.
