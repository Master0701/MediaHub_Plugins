## MediaHub Interaktions-KI v0.1.13 – Windows Compute Node

- Nach ausdruecklich bestaetigter Runtime- und Modellinstallation wird das gewaehlte CPU-/CUDA-Profil in `launch_config.json` gespeichert.
- Lokaler llama.cpp-Server kann beim Chat-Auftrag anhand des bestaetigten Profils automatisch gestartet werden.
- Runtime-Pfad wird aus dem Plugin-Kontext ermittelt; bestehender expliziter Umgebungsvariablen-Start bleibt als Fallback erhalten.
- Vor dem Speichern der Startfreigabe werden Runtime-EXE und GGUF-Modell auf Vorhandensein geprueft.
- Worker-Metadaten kennzeichnen die verwaltete Installation korrekt.
- Kein stillschweigender Download und kein automatischer Start fuer entfernte Endpunkte.

## MediaHub Interaktions-KI v0.1.12 – Windows Compute Node

- Eigenständiges `.mhaiplugin` für `windows_compute` / Windows x64; kein Raspberry-Pi-Plugin und keine feste Integration in den Node.
- Lokaler llama.cpp/GGUF-Chat mit CPU-, GPU-/CUDA- und Auto-Ausführungsprofil.
- Kontrollierte Installation aus lokal vorhandenen Runtime- und Modellarchiven mit SHA256-Prüfung, ZIP-Pfadschutz und ausdrücklicher Bestätigung.
- Einbindung in den bestätigten Installationsplan der Windows Compute Node; keine stillschweigenden Downloads oder Installationen.
- Plugin-Web-Bridge mit lokalem HTTP 8768 und Node-seitigem LAN-HTTPS 8769; die LAN-Adress-, Zertifikats- und Zugangsdatenverwaltung liegt bei der Windows Compute Node.
- Echte CPU- und CUDA-Chat-Inferenz sowie HTTPS-Authentifizierung am 17.11.2026 erfolgreich im Nulltest nachgewiesen.
- **Noch keine GitHub-Veröffentlichung:** `catalog.visible=false` und `auto_install=false` bleiben bis zur expliziten Freigabe bestehen.

## 0.1.11-dev
- Read-only preflight of BOTH ZIP structures before any install target is modified.
- No release or catalog download added.

## v0.1.9-dev
- Separater, sicherer lokaler GGUF-ZIP-Installer mit SHA256, Pfadschutz und expliziter Bestaetigung.
- Noch keine automatische Kataloganbindung oder Modellinstallation im Node-Installer.
- Keine Runtime-Downloads oder Releases.

## 0.1.7-dev
- Windows-Compute-Node-Installer-Integrationspatch (lokales, bestaetigtes Runtime-ZIP).
- Noch keine automatische MediaHub_Tools-Bereitstellung und kein GGUF-Paket.

## 0.1.6-dev (unveroeffentlicht)
- Konsolidierung und Umbenennung zu MediaHub Interaktions-KI
- Bestehende 0.1.5-Funktionen und Tests erhalten
- Keine neue Installer- oder Download-Funktion vor Node-Abgleich

## 0.1.5 – Phase 6
- Vordergrundstart mit ausdruecklichem --confirm-start.
- Read-only Health-Check und Schutz vor Start auf belegtem Port.
- Prozessende bei Ctrl+C, Abbruch bei Startfehlern.
- CPU-/GPU-/Multi-GPU-Parameter aus bestehender Startplanung.
- Keine Installer-, Node- oder Fremdplugin-Aenderungen.

## 0.1.4 – Phase 5
- Explizit freizugebender Windows-Compute-Node-Installer-Adapter.
- Lokales llama.cpp-ZIP mit SHA256, kein Download und keine Ueberschreibung.
- Node-Patch standardmaessig nur Dry-Run; kein Release.

# Änderungen

## 0.1.1 (Entwicklung)
- Read-only llama.cpp-Runtime-Prüfung und sichere Startplanung für CPU, eine oder zwei GPUs.
- Kein Download, keine Installation, kein automatischer Prozessstart.
- Tests für Konfiguration und Sicherheitsgrenzen.

## 0.1.0
- Erster Worker für externen lokalen llama-server.

## 0.1.2 – Phase 3
- SHA-256-verifizierte, rein lesende Installationsplanung fuer lokale llama.cpp-ZIP-Dateien (CPU/CUDA).
- GGUF-Modellpruefung ohne automatische Downloads.
- Keine Integration in produktiven Installer, keine Ausfuehrung oder Installation.

## v0.1.3 – Phase 4
- Explizit bestaetigter lokaler ZIP-Installationsbaustein mit SHA-256, Pfadpruefung und Ueberschreibschutz.
- Noch keine Integration in den Node-Installer und kein Download.

## 0.1.10-dev
- Installer-Adapter installiert nach Freigabe getrennte lokale Runtime- und GGUF-Pakete.
- Beide SHA256-Pruefsummen vor erster Dateiaenderung pruefen.
- Bei Teilfehler keine stille Loeschung.
- Modell-Integrationstests ergaenzt.
