# AI-Node SDK – Referenzplugin

Der vorhandene `MediaHub AI Test Provider` bleibt unverändert.

Das SDK bindet ihn von außen über sein bestehendes `plugin.json` ein:

1. `load_manifest()` liest das Manifest.
2. `load_plugin()` lädt den vorhandenen `entrypoint`.
3. Die Runtime-ID, der Name und die Version werden mit dem Manifest geprüft.
4. Die Capability-Liste wird direkt aus `plugin.json` übernommen.
5. Wenn `health_check` deklariert ist, muss `health()` vorhanden sein.
6. `read_health()` prüft die vorhandene Health-Antwort.

Es gibt keine zweite Capability-Liste und keine neue Basisklasse, von der das
Plugin erben müsste.

Damit bleibt das AI-Node-Plugin-Paket unabhängig vom SDK-Code im Repository.
Das SDK ist die gemeinsame Prüf- und Laufzeitschicht des AI-Node-Systems.
