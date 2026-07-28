# MediaHub KI-Assistent v1.7.0 – Query Reasoner 2.0

## Enthalten

- lokale Alias- und Wissensdaten-Auflösung
- deutsche, englische und Originaltitel aus Entity-Metadaten
- Zerlegung kompakter Titel, CamelCase sowie Buchstaben-/Zahlenfolgen
- Entfernung technischer Zusätze, Episodenmarker, Jahreszahlen und Releasegruppen
- starke Abwertung schwacher Einzelwort-Suchen
- evidenzbasiertes Ranking aus Titel, Suchvariante, Medientyp, Jahr, Staffel/Folge, Laufzeit und Provider-Vertrauen
- Schutz gegen Wikipedia-Zufallstreffer ohne kombinierte Belege
- Diagnosefelder `evidence_count` und `penalties`

## Installation im VS-Code-PowerShell-Terminal

```powershell
cd "D:\eigenes program\MediaHub-Plugins"
Expand-Archive ".\MediaHub_KI_Assistent_v1.7.0_Query_Reasoner_2.0.zip" ".\_query_reasoner_v170" -Force
& ".\_query_reasoner_v170\apply_patch.ps1"
```

## Test

```powershell
python -m pytest plugins/ai_assistant/tests/test_query_reasoner_v2.py -q
python -m compileall plugins/ai_assistant
```

## Build

```powershell
python build_plugins.py ai_assistant --clean
```

Falls der Builder die Plugin-ID statt des Ordnernamens erwartet, alternativ:

```powershell
python build_plugins.py all --clean
```

## Hinweis zum Lernsystem

Der Reasoner liest bereits lokale Aliasregeln aus der bestehenden Knowledge-Engine. Das automatische Speichern einer Benutzerkorrektur muss an der späteren Bestätigungs-/Korrekturaktion angeschlossen werden, weil diese GUI-/API-Aktion nicht Bestandteil der bereitgestellten Prüfdateien war. Die Suchseite ist dafür vorbereitet und verwendet neu gespeicherte Aliase automatisch beim nächsten Lauf.
