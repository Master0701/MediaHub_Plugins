# MediaHub Python Runtime (Windows Compute Node)

Gemeinsame portable Python-3.12.10-x64-Basis fuer SmolVLM2, GLiNER und Speech-to-Text.

## Entwicklungsstand

Die lokale, **explizit bestaetigte** Installation aus einem bereits vorhandenen ZIP
ist als `plugin.install_local_archive(package, expected_sha256, confirmed=True)`
vorhanden. Der Zielpfad wird von `runtime_root()` bestimmt. Existierende
Installationen werden nicht ersetzt. Vor und nach der Installation werden
Archiv bzw. Python-Laufzeit geprueft.

**Noch nicht fertig:** Offizielle reproduzierbare Paketquelle, Lizenz- und
Provenienzpruefung, Download und Anbindung an die bestaetigte Compute-Node-
Installationsplanung. Deshalb gibt es absichtlich **keinen automatischen Download**
und **keine automatische Installation beim Laden des Plugins**. Ein SHA256-Wert
allein beweist nicht die Herkunft eines Archivs.

Das offizielle `python-3.12.10-embed-amd64.zip` ist **kein Ersatz**: Es enthaelt
keine vollstaendige `venv`-/`ensurepip`-Runtime. Das bisherige lokale Test-ZIP
ist **kein freigegebenes Release-Artefakt**.

Keine Windows-Systeminstallation, keine PATH-/Registry-Aenderung und keine
Aenderung am Raspberry-Pi-Installer.

## MediaHub_Tools Download (v0.1.2)

Der opt-in Download aus `Master0701/MediaHub_Tools` ist verfuegbar. Er prueft
zunaechst das `packages/python/current/manifest.json` gegen fest hinterlegte
Version, Paketname, Groesse und SHA256. Danach wird das offizielle GitHub-
Release-Asset geladen, erneut anhand SHA256 und ZIP-Inhalt kontrolliert und
nur nach ausdruecklicher Bestaetigung parallel installiert.

Aufruf (nur auf ausdruecklichen Wunsch):

`python install_parallel_runtime.py --from-tools --confirm --runtime-base <Compute-Runtime-Verzeichnis>`

Keine Installation beim Plugin-Laden, keine Aenderung an System-Python,
keine Ersetzung bestehender Runtime. Die automatische Ausloesung durch die
Compute-Node-Plugin-Installationsplanung ist ein separater Integrationsschritt;
dieses Paket allein fuehrt noch keine stille Installation aus.
