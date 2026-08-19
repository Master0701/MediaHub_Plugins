# MediaHub Plugins v0.5.12 – vollständiges Release

## MediaHub KI-Assistent v7.0.8

- Filmidentifikation bei technisch erweiterten oder verschmutzten Dateinamen verbessert.
- Strukturierte Identity-Hints werden vor der Online-Suche berücksichtigt.
- Query-Reasoner priorisiert bestätigte Identity-Hints gegenüber schwachen Dateinamen-Fallbacks.
- Identity-Hints werden auch bei Treffern aus dem Analyse-Cache korrekt angewendet.
- Filmtitel und Erscheinungsjahr werden zuverlässiger aus der erkannten Medienidentität übernommen.
- Editions-/Fassungserkennung für Angaben wie Remastered verbessert.
- Editionshinweise können zusätzlich aus bereits vorhandenen lokalen Metadaten übernommen werden.
- Online-Metadaten und Filmcover werden nach erfolgreicher Identifikation zuverlässiger gefunden.
- Neue Regressionstests für verifizierte Medienidentität und Query-Reasoning ergänzt.
- Temporäre Laufzeit-Debugausgaben entfernt.

## MediaHub Audio Metadata Editor v0.0.1

- Funktionsstand unverändert.
- Manifest und gemeinsamer Plugin-Katalog wurden im aktuellen Repository-Stand berücksichtigt.
- Wird mit dem vollständigen Release erneut gebaut und validiert.

## MediaHub Metadata Editor v0.4.4

- Neues sichtbares Grunddatenfeld „Fassung / Edition“.
- Unterstützt unter anderem Remastered, Extended, Uncut und Director's Cut.
- KI-Vorschläge für Fassung/Edition werden in das echte Editor-Feld übernommen.
- Anzeige „Veröffentlichung / Ausstrahlung“ auf korrekte UTF-8-Darstellung repariert.
- GUI- und UTF-8-Regressionstests ergänzt.
- Temporäre KI-Debugausgabe aus der Metadatenvorschau entfernt.

## MediaHub Mobile Dashboard v0.1.7

- Funktionsstand unverändert.
- Wird mit dem vollständigen Release erneut gebaut und validiert.

## MediaHub Smart Renamer v0.5.17

- Funktionsstand unverändert.
- Wird mit dem vollständigen Release erneut gebaut und validiert.

## MediaHub WebRemote v0.13.7

- Funktionsstand unverändert.
- Wird mit dem vollständigen Release erneut gebaut und validiert.

## MediaHub AI Test Provider v1.0.0

- AI-Node-Plugin.
- Funktionsstand unverändert.
- Wird getrennt als AI-Node-Plugin validiert und gemeinsam mit den MediaHub-Plugins veröffentlicht.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.
