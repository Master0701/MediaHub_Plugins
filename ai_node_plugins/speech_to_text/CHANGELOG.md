# Changelog

## 0.1.3

- Bereits vorhandene Manifestversion 0.1.3 dokumentiert; keine erneute Versionsanhebung.
- Isolierte Speech-Laufzeit auf Basis von faster-whisper 1.2.1 und av 16.0.1 im aktuellen Manifest deklariert.
- Die genaue Abgrenzung der Codeaenderungen zwischen 0.1.2 und 0.1.3 ist noch anhand der lokalen Git-Historie zu verifizieren.

## 0.1.2 (nachtraeglich dokumentierter Entwicklungsstand)

- Windows-/Raspberry-Pi-Kompatibilitaet, Node-Worker, UTF-8-Verarbeitung und private Python-Laufzeit wurden in der Entwicklung bearbeitet.
- Trennung von Speech-Paketen und gemeinsamem Python-Basisinterpreter als Architekturziel dokumentiert; kein unbelegter Vollzug behauptet.
- Fruehere echte faster-whisper-CPU-Transkription auf Raspberry Pi mit vier Threads erfolgreich getestet.


## 0.1.1

- Worker-Status verwendet jetzt die isolierte Speech-Laufzeit zur Ermittlung der `faster-whisper`-Verfügbarkeit.
- Behebt die falsche Anzeige `engine.available = false`, obwohl die isolierte Laufzeit einsatzbereit ist.
- Pakettests um README, Changelog, Lizenz und Requirements erweitert.


## 0.1.0

- Erste Version des gemeinsamen MediaHub Speech-to-Text-Plugins.
- Unterstützung für Raspberry Pi AI-Node.
- Unterstützung für Windows Compute Node.
- Isolierte `faster-whisper`-Laufzeit.
- CPU- und GPU-Ausführungsmodi.
