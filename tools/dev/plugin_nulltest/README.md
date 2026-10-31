# MediaHub Plugin-Nulltest v1.0.0

Eigenstaendiges Windows-Testwerkzeug fuer sechs Nullinstallationen mit echten Inferenz-/API-Auftraegen: GLiNER CPU/GPU, SmolVLM2 CPU/GPU und Speech-to-Text CPU/GPU.

## Voraussetzungen
- Windows mit Windows PowerShell 5.1, Schreibrechten fuer einen separaten Testordner, Internetzugang und ausreichend freiem Speicherplatz.
- Fuer GPU-Tests: kompatible NVIDIA-GPU und funktionsfaehiger Treiber. CPU-Tests brauchen keine NVIDIA-GPU.
- Die MediaHub-Projekte muessen unter `D:\eigenes program\MediaHub-Plugins` und `D:\eigenes program\MediaHub-AI-Node` liegen; das Skript verwendet diese Pfade derzeit fest.
- Die passenden `.mhaiplugin`-Builds muessen im `MediaHub-Plugins\release`-Ordner liegen. Die Compute-Node-EXE wird aus dem Build-Ausgabeordner des Node-Projekts verwendet.
- Es sind echte Installationen und Modell-Downloads; ein Test kann laenger dauern.

## Start
1. ZIP entpacken und PowerShell oeffnen.
2. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<Pfad>\MediaHub_Gemeinsamer_Nulltest_v1.0.0.ps1" -Mode all` ausfuehren.
3. Separaten Testordner auswaehlen, die Rueckfragen beachten und den Durchlauf abwarten.
4. Die erzeugten Ergebnisprotokolle pruefen. `PASS` bedeutet erfolgreicher Installations- und Inferenz-/API-Test.

Alternativen: `-Mode cpu` oder `-Mode gpu`.

## Hinweise
- Das Skript ist ein Testwerkzeug und kein MediaHub-Plugin. Es wird als separates ZIP im Plugin-Release angeboten.
- Es erstellt Testordner, installiert Abhaengigkeiten und laedt Modelle herunter. Es veroeffentlicht keine GitHub-Releases.
- Keine Aenderungen am Raspberry-Pi-Installer.
- Die Testskriptlogik entspricht RC5; fuer v1.0.0 wurde nur die Versionsangabe aktualisiert.
- Bei abweichenden lokalen Repository-Pfaden ist vor Nutzung eine gezielte Pfadanpassung erforderlich.
