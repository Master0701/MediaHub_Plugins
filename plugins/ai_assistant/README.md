# MediaHub KI-Assistent v1.6.1

Der KI-Assistent verbindet Medienerkennung, In-Video-Planung und eine neue Quality Engine.

## Neu in v1.0.0

- Decision Engine mit gewichteten, unabhängigen Beweisen
- Widerspruchserkennung zwischen Dateiname, Online-Treffern und Videoinhalt
- nachvollziehbare Gesamtsicherheit und Vertrauensstufe
- korrigierter Supervisor-Abschlussstatus
- In-Video-Manager mit getrennten Frame-, OCR-, Untertitel-, Audio-, Fingerprint- und Szenenagenten
- gemeinsamer Analyseplan, damit Medienerkennung und Qualitätsprüfung dieselben Daten verwenden
- aktive technische Bildqualitätsbewertung
- aktive technische Audioqualitätsbewertung
- getrennte Bild-, Ton- und Gesamtpunktzahl
- Status: sehr gut, gut, noch akzeptabel, verbesserungswürdig oder neu in besserer Qualität suchen
- persönliche Referenzprofile werden lokal vorbereitet und gespeichert
- Qualitätsentscheidungen führen niemals automatisch zu Löschung oder Austausch

## Nächste Ausbaustufe

Für v1.0.0 folgen die stabilen Plugin-Schnittstellen zum Metadata Editor und Universal Renamer, die Wissensbeziehungen sowie die abschließenden Release- und Lizenzprüfungen.


Optional können Umgebungsvariablen gesetzt werden:

- `MEDIAHUB_TMDB_API_KEY` oder `MEDIAHUB_TMDB_BEARER_TOKEN`
- `MEDIAHUB_TVDB_API_KEY`
- `MEDIAHUB_TVDB_SUBSCRIBER_PIN` nur bei einem entsprechenden TheTVDB-Schlüssel

Wikipedia ist standardmäßig aktiviert und benötigt keinen Schlüssel.

## v1.0.0 – stabile KI-Grundarchitektur

- Erklärbare Entscheidung mit Begründung, Einschränkungen und Widersprüchen
- Lokale Fingerprint-Referenzdatenbank; Einträge nur nach Benutzerbestätigung
- Stabile Integrations-API (Schema 1) für Metadata Editor und Universal Renamer
- Keine automatische Änderung ohne Vorschau und Bestätigung
- Supervisor, Decision Engine und ausgeführte Agenten verwenden denselben finalen Zustand

## Backend- und Task-Grundlage

Die interne MediaHub-KI bleibt Standard- und Fallback-Backend. Der optionale
Raspberry-Pi-AI-Node wird erkannt, lokale Dateien werden jedoch erst nach
sicherer Dateiübergabe oder über einen erreichbaren Pfad remote verarbeitet.

Jede Analyse erhält eine Task-ID, Backend-Angabe und Zeitstempel.

## Tool- und Capability-Verwaltung

Der KI-Assistent ordnet Funktionen jetzt zentral den benötigten Werkzeugen zu.
Pflichtwerkzeuge und optionale Funktionen werden getrennt ausgewiesen.

Beispiele:

- Basisanalyse: FFprobe und MediaInfo
- Frame-Analyse: FFmpeg und FFprobe
- OCR: FFmpeg und Tesseract
- MKV-Analyse: MKVToolNix
- Qualitätsbewertung: FFprobe und MediaInfo

Fehlende optionale Werkzeuge deaktivieren nur die zugehörige Funktion.
Fehlende Pflichtwerkzeuge werden im Status deutlich ausgewiesen.

## Sichtbare Backend- und Capability-Anzeige

Im Hauptfenster befindet sich jetzt der Reiter **Backends & Fähigkeiten**.
Er zeigt Backends, verfügbare und fehlende Funktionen, Werkzeuge sowie
Task-Zähler. Der bisherige rohe JSON-Systemstatus bleibt erhalten.

## Automatische AI-Node-Verbindung

Der KI-Assistent übernimmt Host, API-Port und API-Token automatisch aus den
globalen MediaHub-Einstellungen. Die Verbindung wird beim Statusabruf und vor
jeder Analyse neu eingelesen.

## AI-Node-Diagnose

Version und Name werden vom Root-Endpunkt gelesen. Der Health-Endpunkt liefert
Pluginzahlen, CPU, RAM, Datenträgerstatus und Temperatur. Zusätzlich wird die
Antwortzeit gemessen. Capability-IDs erscheinen mit verständlichen deutschen
Bezeichnungen.

## Lokaler Orchestrator

Version 1.2.0 führt die zentrale lokale Steuerungsschicht ein. Eine KI-Anfrage
wird zuerst in nachvollziehbare Teilschritte zerlegt. Jeder Schritt enthält
die benötigte Fähigkeit und die dafür erforderlichen Werkzeuge.

In dieser Version wird ausschließlich die lokale MediaHub-KI verwendet.
AI-Node und Cloud werden nicht zur Ausführung herangezogen.

## Agent-Manager

Der Agent-Manager registriert alle lokalen Analyse-, Wissens-, Qualitäts- und
Entscheidungsagenten. Für jeden Agenten werden Fähigkeit, benötigte Werkzeuge,
Implementierungsstand und mögliche Parallelausführung verwaltet.

Bereits vorhandene Analyseagenten werden als implementiert erkannt.
Wissensdatenbank-, Online- und Supervisor-Agent bleiben registriert, werden
aber bis zu ihrer vollständigen Anbindung als ausstehend gekennzeichnet.

## Wissens-Engine

Die lokale Wissens-Engine speichert Filme, Serien, Staffeln, Folgen und andere
Medientypen als Wissensobjekte. Beziehungen werden getrennt erfasst, darunter:

- Franchise und gemeinsames Universum
- Spin-off, Prequel und Sequel
- Crossover
- Remake und Reboot
- alternative Zeitlinien
- Fortsetzung oder Beginn in einer bestimmten Serie bzw. Folge

Reihenfolgen werden nicht vermischt, sondern getrennt gespeichert:

- chronologische Reihenfolge innerhalb der Handlung
- Veröffentlichungsreihenfolge
- empfohlene Anschau-Reihenfolge
- benutzerdefinierte Reihenfolge

Damit können beispielsweise Star Trek, Stargate, NCIS, CSI, Doctor Who oder
Rocky/Creed mehrere korrekte Reihenfolgen gleichzeitig besitzen.

## Getrennte Wissensspeicher

Die vorhandene Datei `knowledge.sqlite3` bleibt vollständig erhalten.
Der neue Wissensgraph wird parallel gespeichert:

```text
knowledge.sqlite3
knowledge_graph/knowledge_graph.json
```

## Wissensschema-Initialisierung

Die Wissens-Engine legt `knowledge_graph/knowledge_graph.json` beim Start automatisch an. Die vorhandene `knowledge.sqlite3` bleibt unverändert.

## Vollständige Wissens-API-Kompatibilität

Die Wissens-Engine stellt alle bereits von Plugin-GUI und Web-API verwendeten
Methoden bereit: Initialisierung, Status, Statistik, vollständige Auflistung,
Suche und idempotente Beispieldaten. Die vorhandene `knowledge.sqlite3` bleibt
unverändert; der neue Wissensgraph wird atomar in
`knowledge_graph/knowledge_graph.json` gespeichert.


## Provider Framework

Provider werden zentral registriert und parallel ausgeführt. Timeouts, Cache und Laufzeitdiagnosen werden einheitlich verwaltet.

## Intelligente Quellenauswahl

Unbekannte Medientypen blockieren keine Onlinesuche mehr. Vorhandene
Titelhinweise werden medientypübergreifend gegen Film-, Serien- und
Hörbuchquellen geprüft.

Bei Cachetreffern bleiben technische und In-Video-Ergebnisse erhalten.
Quellenplan, Online-Ranking, Supervisor und Entscheidung werden mit dem
aktuellen Pluginstand neu berechnet.


## Suchvarianten-Reasoner

Dateinamen und lesbare OCR-Hinweise werden in gewichtete Suchvarianten zerlegt. Provider speichern die jeweils verwendete Variante am Treffer.

## Multi-Query-Ausführung

Der Online-Agent verwendet exakt den zuvor geplanten Quellenquery. Alle
gewichteten Suchvarianten werden gegen jeden geeigneten Provider ausgeführt.
Providerergebnisse führen die einzelnen Abfragen unter `queries` auf.
Jeder Treffer speichert die Suchvariante, über die er gefunden wurde.
