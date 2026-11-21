# MediaHub Interaktions-KI v0.1.13

**Bisheriger Nulltest (17.11.2026):** Lokaler Chat über llama.cpp/GGUF auf der Windows Compute Node wurde in getrennten CPU- und CUDA-Nullinstallationen erfolgreich getestet. Das Plugin bleibt ein separat installierbares `.mhaiplugin` und ist im Katalog sichtbar, aber nicht automatisch installierbar (`catalog.visible=true`, `auto_install=false`).

Die Installation verwendet lokal bereitgestellte, SHA256-verifizierte Runtime- und GGUF-Archive mit ausdrücklicher Bestätigung über die Node-Installationsplanung. Es gibt keinen stillschweigenden Modell-Download. Die lokale Web-Bridge läuft über HTTP 127.0.0.1:8768; die Windows Node stellt zusätzlich passwortgeschütztes HTTPS auf der automatisch erkannten LAN-Adresse, Port 8769, bereit. Zertifikat und Zugangsdaten verwaltet die Node, nicht das Plugin.

**Nachweis:** CPU-Modus `owned_llama_process_cpu_mode_gpu_layers_0`; CUDA-Modus `llama_cpp_startup_log_offloaded_layers`. Beide Tests lieferten eine echte Chat-Antwort; HTTPS antwortete ohne/falsch authentifiziert mit 401 und mit gültigen Zugangsdaten mit 200.

**Drittanbieter:** llama.cpp ist MIT-lizenziert; GGUF-Modelle besitzen eigene, modellabhängige Lizenzbedingungen. NVIDIA CUDA unterliegt gesonderten Bedingungen. Details in `THIRD_PARTY_LICENSES.md` des Node- und Plugin-Repositories.

**Neu in v0.1.13:** Nach ausdruecklich bestaetigter Installation speichert das Plugin das CPU-/CUDA-Profil und kann den lokalen llama.cpp-Server bei Chat-Auftraegen automatisch starten. Kein automatischer Download; entfernte Endpunkte sind ausgeschlossen.

## Historische Entwicklungsnotizen

Die folgenden Phasenbeschreibungen sind historische Momentaufnahmen; Aussagen wie „Integration noch offen“ oder „CPU/CUDA-Test noch ausstehend“ beziehen sich nicht mehr auf den frueheren Stand v0.1.12.

# MediaHub Interaktions-KI – Phase 1

Dieses erste Entwicklerpaket implementiert einen echten Compute-Node-Worker fuer `chat` und `text_generation`. Es verbindet sich ausschliesslich mit einem **bereits gestarteten lokalen** llama.cpp `llama-server` auf Port 8080. Es installiert **nichts**, startet **keinen** Server und laedt **keine** Modelle herunter.

Voraussetzungen fuer einen echten Modelltest: llama-server lokal auf `127.0.0.1:8080` mit einem bereits vorhandenen GGUF-Modell gestartet. Die Phase-1-Registrierung prueft nur den Worker-Vertrag; ein nicht laufender Server fuehrt bei Jobs zu einem klaren Fehler. Die Worker-Metadaten kennzeichnen diese eingeschraenkte Bereitschaft; sie sind noch kein Health-Check.

## Geplante Folgephasen

- Verifizierte, bestaetigungspflichtige llama.cpp CPU-/CUDA-Installation und GGUF-Modellverwaltung; eigener Plugin-Runtime-Lebenszyklus.
- Automatische Hardware-Erkennung und explizite GPU-Auswahl; Multi-GPU-Verteilung mittels `--device`, `--split-mode` und `--tensor-split`.
- Job-Health-Check, Streaming, Cancel, Timeouts, Sleep/Wake, Ressourcenlimits.
- Getrennte Regeln fuer automatische Medienaktionen; keine Dateiaenderungen durch dieses Plugin.
- Optionale Kopplung mit dem bereits vorhandenen Speech-to-Text-Plugin.
- Nulltest v1.0.3 erweitern, sobald die lokale Version vorliegt.
- Raspberry Pi: in dieser Phase nicht als Ziel deklariert; Pi-Installer bleibt unveraendert.

## Installation fuer Entwickler

Ordner `ai_node_plugins/interaktions_ki` in den gleichen Pfad im `MediaHub_Plugins`-Arbeitsbaum uebernehmen. Die bestehende Build-Logik entdeckt das Manifest. Aktueller Manifest-Stand: `catalog.visible=true` und `auto_install=false`.

## Sicherheit

Keine Dateisystem-Schreiboperationen, kein Modell-Download, keine Shell-Ausfuehrung. Serververbindung nur zu localhost:8080. Ein fremder Prozess auf diesem Port kann jedoch auf die gesendeten Texte zugreifen; nur auf vertrauenswuerdigen lokalen Installationen testen.


## Phase 2: Startplan (noch keine Installation)
`runtime_manager.plan_launch(...)` erzeugt ausschließlich eine validierte Befehlsliste. Die tatsächliche llama.cpp-Binary, ein GGUF-Modell und CUDA-Verfügbarkeit werden noch nicht automatisch beschafft oder geprüft. GPU-Namen wie CUDA0/CUDA1 sind Platzhalter und müssen mit `llama-server --list-devices` am Zielrechner bestätigt werden. Bestehende Chat-Funktion nutzt weiterhin einen bereits laufenden lokalen Server auf Port 8080.

## Phase 3: Installationsplanung
`install_plan.py` erstellt nur Plaene fuer bereits lokal vorhandene ZIP-/GGUF-Dateien und prueft optional SHA-256. Es installiert oder entpackt nichts. Die Integration in den bestaetigten Node-Installer und echte CPU-/CUDA-Tests sind weiterhin offen. Fuer ein echtes Installationspaket sind sichere ZIP-Pfadpruefung, Release-Provenienz und Lizenzpruefung Pflicht.

## Phase 4 (v0.1.3)
`safe_install.install_local_archive` ist ein eigenstaendiger, explizit bestaetigungspflichtiger lokaler Installationsbaustein. Er ist **noch nicht** an den Node-Installer angeschlossen. Nur lokal bereitgestellte und mit unabhaengig vertrauenswuerdigem SHA-256 abgesicherte ZIP-Dateien werden akzeptiert. Der Backend-Health-Check und die CPU/CUDA-Pruefung stehen noch aus. Keine automatische Installation durch Plugin-Jobs.

## Entwicklungsstand v0.1.6-dev
Bestehender Code v0.1.5 erhalten. Plugin-ID, sichtbarer Name, Worker-ID und Entrypoint konsistent umbenannt. Runtime-Paket und GGUF-Modell werden weiterhin NICHT automatisch heruntergeladen. Die Integration mit dem tatsaechlichen Windows-Compute-Node-Installer und MediaHub_Tools ist noch offen. Keine produktive Installation oder Veroeffentlichung.
