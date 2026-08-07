# AI-Node SDK – Capability-Methoden-Verträge

Der vorhandene Testprovider zeigt einen wichtigen Unterschied:

- Capability im Manifest: `test_provider`
- vorhandene Python-Methode: `test()`

Das ist kein Fehler im Plugin. Eine Capability beschreibt eine Fähigkeit,
nicht zwingend den Python-Methodennamen.

Deshalb besitzt das SDK eine kleine Liste standardisierter
Capability-Methoden-Verträge, z. B.:

- `health_check` -> `health()`
- `test_provider` -> `test()`

Wichtig: Diese Zuordnung ist **keine zweite Capability-Liste**.

Ob ein Plugin `test_provider` tatsächlich besitzt, wird weiterhin
ausschließlich aus seinem `plugin.json` gelesen. Die Zuordnung sagt nur,
welche Runtime-Methode für eine bereits deklarierte Capability aufgerufen
werden soll.

Neue Plugins können alternativ einen einheitlichen `execute(task_type,
payload)`-Einstieg bereitstellen. Bestehende Plugins müssen dafür nicht
verändert werden.
