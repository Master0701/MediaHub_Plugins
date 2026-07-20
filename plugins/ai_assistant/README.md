# MediaHub KI-Assistent v0.6.0

- Kostenmodell für alle Erkennungsagenten ergänzt.
- Supervisor plant Agenten nach Sicherheit, Nutzen und Aufwand.
- Aktivierte und konfigurierte Online-Provider werden automatisch ausgeführt.
- Provider werden nach Medientyp und Priorität ausgewählt.
- Treffer verschiedener Quellen werden vereinheitlicht und gemeinsam bewertet.
- In-Video-Erkennung bleibt als verpflichtende Eskalationsstufe für unklare Fälle vorgesehen.

# MediaHub KI-Assistent 0.4.1

Erste testbare Grundversion von Plugin 4.

## Enthalten

- automatische Anlage von `config/knowledge.sqlite3`
- WAL-Modus und gezielte Indizes für schnelle SQLite-Abfragen
- versioniertes Datenbankschema
- ausschließlich lesender Zugriff auf `config/mediahub.sqlite3`
- eigenes Desktop-Fenster mit Systemstatus
- vorbereitete Tabellen für Medien, Beziehungen, Editionen und Erkennungs-Cache
- keine feste Abhängigkeit von einem KI-Anbieter

## Noch nicht enthalten

Die eigentliche Film-/Serien- und Editionserkennung wird schrittweise auf diesem Grundsystem aufgebaut.

## Neue Medienerkennung in v0.4.2

Die lokale Erstprüfung erkennt jetzt Filme, Serien, Mehrfachfolgen, Specials, Staffel-/Folgenmuster und viele Schnittfassungen. Unsichere Ergebnisse werden ausdrücklich für den späteren Datenbank- oder Webabgleich markiert.

## Mehrquellen- und Agentenarchitektur ab v0.5.0

Die Datei `config/sources.json` verwaltet eingebaute sowie frei definierbare Quellen. Online-Abfragen sind in v0.5.0 bewusst noch nicht automatisch aktiv. Der Supervisor plant anhand der lokalen Erkennung, ob Online-Quellen oder die spätere In-Video-Erkennung benötigt werden.

Die In-Video-Pipeline ist als Kernfunktion vorbereitet und umfasst Schlüsselbilder, OCR, Untertitel, Audio-/Spracherkennung, Bild-/Ton-Fingerprints und Schnittfassungsvergleiche.
