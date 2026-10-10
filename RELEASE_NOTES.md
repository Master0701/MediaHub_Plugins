# MediaHub Plugins v0.5.20 – vollständiges Release

## MediaHub KI-Assistent v7.0.11

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Audio Metadata Editor v0.0.1

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Metadata Editor v0.4.5

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Smart Renamer v0.5.18

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub GLiNER v0.1.1

- Automatische Bereitstellung der Linux-ARM64-CPU-Runtime aus MediaHub_Tools ergänzt.
- Runtime-Download, Paketprüfung und sichere Entpackung integriert.
- Kontrollierte Runtime-Aktivierung mit Backup-/Rollback-Vorbereitung ergänzt.
- Automatische Installation auf Raspberry Pi 5 mit Python 3.13 erfolgreich getestet.
- GLiNER und PyTorch nach automatischer Installation erfolgreich geprüft.

- Neues AI-Node-Plugin für lokale semantische Entitäts- und Identitätserkennung.
- Stellt die Capability `semantic_text_analysis` für den MediaHub-KI-Assistenten bereit.
- Unterstützt die gemeinsame GLiNER-Runtime aus dem MediaHub-Tools-Repository.
- Unterstützt Windows Compute Node sowie Linux ARM64 / Raspberry Pi über die gemeinsame Runtime-Verwaltung.
- Runtime und Modell werden nicht unnötig im Plugin-Paket gebündelt, sondern über die vorgesehene Tool-/Runtime-Verwaltung bereitgestellt.

## MediaHub AI Test Provider v1.0.0

- Unveränderter AI-Node-Plugin-Stand in diesem Release.

## MediaHub SmolVLM2 Vision v0.1.1

- Runtime-Verwaltung und automatische Python-Bereitstellung erweitert.
- Python-Bootstrap und isolierte Runtime-Provisionierung ergänzt.
- Modellverwaltung und Runtime-Profile überarbeitet.
- Modellpaket-Version 0.1.0 bleibt unverändert.

- Neues AI-Node-Plugin für lokale Bild-, Vision- und Video-Frame-Analyse.
- Unterstützt MediaHub AI Nodes und Windows Compute Nodes.
- Verwendet SmolVLM2-500M-Video-Instruct über die gemeinsame MediaHub-Tools-Modellverwaltung.
- Unterstützung für Video-Frame-Analyse und kontrollierte Frame-Verarbeitung ergänzt.
- Das für die Video-Frame-Verarbeitung benötigte FFmpeg wird bewusst direkt im Plugin-Paket mitgeliefert.
- Modellbereitstellung, Runtime-Status und Runtime-Provisionierung sind in die Plugin-Infrastruktur integriert.
- Große Modelldateien werden nicht im Plugin-Paket gebündelt, sondern über die vorgesehene Tool-/Modellverwaltung bereitgestellt.

## MediaHub Speech-to-Text v0.1.2

- Unveränderter AI-Node-Plugin-Stand in diesem Release.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.
