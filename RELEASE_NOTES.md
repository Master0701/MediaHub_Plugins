# MediaHub Plugins v0.5.17 – vollständiges Release

## MediaHub KI-Assistent v7.0.11

- Neue Lernroutine zum kontrollierten Einlesen ganzer Medienordner mit Warteschlange für manuelle Prüfung.
- Lernscan läuft außerhalb des GUI-Hauptthreads und blockiert MediaHub während längerer Analysen nicht mehr.
- Lernscans können pausiert, fortgesetzt und sauber abgebrochen werden; beim Schließen von MediaHub wird ein laufender Scan kontrolliert beendet.
- Bereits bekannte bzw. bereits entschiedene Dateien werden bei späteren Scans erkannt und können gezielt erneut freigegeben werden.
- Lernfälle zeigen eine verständliche Metadatenansicht statt interner Rohdaten, unter anderem Medientyp, Titel, Serie, Staffel, Episode, Episodentitel, Jahr, Quellen und Confidence.
- Entscheidungen `Richtig`, `Falsch`, `Korrigieren` und `Später` sind vollständig mit der persistenten Lernwarteschlange und Historie verbunden.
- Manuelle Korrekturen unterstützen Medientyp, Titel, Serie, Staffel, Episode, Episodentitel und Jahr.
- Bestätigte oder korrigierte Lernfälle werden in das bestehende bestätigte KI-Lernen und den Knowledge Graph übernommen.
- Serienepisoden werden beim Lernen sauber auf die Serienidentität bezogen; Staffel, Episode und Episodentitel bleiben als konkrete Episodeninformationen erhalten.
- Neue Historienansicht `Letzte Lernentscheidungen` zeigt bereits abgeschlossene Lernfälle mit verständlichem Entscheidungsstatus.
- Eine einzelne Lernentscheidung kann mit `Entscheidung zurücknehmen & neu prüfen` gezielt zurückgenommen werden, ohne andere Lernfälle pauschal zu löschen.
- `Falsch`- und `Später`-Entscheidungen können einzeln zurückgenommen werden; die betreffende Datei wird anschließend für einen neuen Lernscan freigegeben.
- Bestätigte Lernbeiträge werden fallgenau über ihre Review-ID verfolgt und mit der zugehörigen Knowledge-Identität sowie Graph-Entität verbunden.
- Mehrere bestätigende Dateien derselben Identität werden per Referenzzählung geschützt: Das Zurücknehmen eines einzelnen Falls löscht gemeinsam gestütztes Wissen nicht.
- Beim Zurücknehmen des letzten ungeschützten Lernbeitrags wird die zugehörige gelernte Identität zentral über den bestehenden Identity-Cleanup bereinigt.
- Bereits vor Einführung des fallgenauen Trackings vorhandenes Wissen wird durch einen späteren einzelnen Undo-Vorgang nicht versehentlich gelöscht.
- Fallbezogene Dateinamen-Aliase werden beim Undo nur dann entfernt, wenn kein anderer aktiver Lernfall denselben Alias weiter bestätigt.
- Bereits vorhandene Aliase bleiben geschützt.
- Doppelte gelernte Filmidentitäten durch nullable Staffel-/Episodenfelder werden verhindert; vorhandene Identitäten werden jetzt direkt aktualisiert statt dupliziert.
- Praktisch getestet: Ein einzelner bestätigter Serienfall wird vollständig zurückgenommen und zentral bereinigt.
- Praktisch getestet: Bei mehreren Bestätigungen derselben Identität bleibt das gemeinsame Wissen erhalten, wenn nur ein Lernfall zurückgenommen wird.
- Praktisch getestet: Chappie blieb bei Rücknahme eines einzelnen bestätigenden Falls erhalten, während nur der fallbezogene neue Alias entfernt wurde.
- Die Plugin-Beschreibung wurde auf die aktuelle Medienerkennung mit In-Video-/Speech-Analyse, Knowledge Graph und kontrollierter Lernroutine aktualisiert.

## MediaHub Audio Metadata Editor v0.0.1

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Metadata Editor v0.4.4

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Mobile Dashboard v0.1.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Smart Renamer v0.5.17

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub WebRemote v0.13.7

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub AI Test Provider v1.0.0

- Unveränderter Plugin-Stand in diesem Release.

## MediaHub Speech-to-Text v0.1.2

- Unveränderter Plugin-Stand in diesem Release.
- Gemeinsames `.mhaiplugin` für Windows Compute Node und Raspberry-Pi-/Linux-AI-Node bleibt erhalten.

## Gemeinsamer Release-Stand

- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.
- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`- oder `.mhaiplugin`-Datei und eine `.sha256`-Prüfsumme bereit.
- Die MediaHub- und AI-Node-Plugin-Kataloge wurden aus den aktuellen Manifesten erzeugt.
- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.
