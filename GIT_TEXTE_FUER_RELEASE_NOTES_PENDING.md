## Gemeinsamer Build- und Teststand

- MediaHub Plugin-Nulltest v1.0.25: PowerShell-5.1-Syntax und separater ZIP-Build inklusive SHA256-Erzeugung am 24.11.2026 bestanden.
- Interaktions-KI v0.1.13: CPU und CUDA mit echter Inferenz, Backend-Nachweis, HTTPS-Authentifizierung und nativem Node-/HTTPS-Tool-Calling bestanden; CUDA drei Wiederholungen.
- Simuliertes Werkzeug `get_test_temperature` (21,5 °C); keine echten ioBroker-Geraete angesprochen.
- Nach Testende Ports 8766 bis 8769 freigegeben und temporaere Zugangsdaten entfernt; vorhandene Firewallregel nicht geaendert.
- Release-Assistent: hoechste eindeutige Nulltest-Version wird ohne `ACTIVE_NULLTEST.txt` automatisch ausgewaehlt; ZIP-Inhalt und SHA256 werden verifiziert; GitHub-Release-Notizen erhalten dynamische Nulltest-Version.
- `-DiagnoseAlle` und vollstaendige Tests der uebrigen Plugin-Profile sind noch offen und werden nicht als bestanden ausgewiesen.

Hinweis: Diesen Abschnitt in die BESTEHENDE RELEASE_NOTES_PENDING.md integrieren, nicht die Datei ersetzen. Plugin-spezifische Versionsabschnitte und die Release-Tag-Version unveraendert erhalten und vor Freigabe pruefen.
