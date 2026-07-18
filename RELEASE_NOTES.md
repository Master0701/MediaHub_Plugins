# MediaHub Plugins – vollständiges Release

## MediaHub WebRemote v0.13.7

- Eigene Desktop-Weboberfläche bleibt über die normale Plugin-Verwaltung direkt öffnbar.
- WebRemote bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Browserbasierte Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben erhalten.

## MediaHub Mobile Dashboard v0.1.7

- Eigene mobile Oberfläche für Handy und Tablet bleibt direkt öffnbar.
- Mobile Dashboard bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Mobile Plugin-Verwaltung und zusätzliche Web-Plugin-Oberflächen bleiben erhalten.

## MediaHub Metadata Editor v0.3.6

- Desktop- und Weboberfläche bleiben gemeinsam verfügbar.
- Der Metadata Editor bleibt in WebRemote und Mobile Dashboard als zusätzliche Plugin-Oberfläche sichtbar.
- Die Weboberfläche öffnet weiterhin in einem neuen Browser-Tab.

## MediaHub KI-Assistent v0.4.1

- KI-Assistent vollständig in den gemeinsamen Plugin-Build und Release aufgenommen.
- Web-Wissenssuche repariert und lokaler Wissensindex im Browser filterbar gemacht.
- Suchen nach Titeln, Aliasnamen und Beziehungen funktionieren direkt in der Weboberfläche.
- Werkzeuganforderungen für FFprobe, MediaInfo, Tesseract OCR und MKVToolNix werden strukturiert über `plugin.json` gemeldet.
- Erfordert MediaHub v1.0.15 mit zentraler Toolverwaltung und portabler Tool-Installation.

## Gemeinsamer Release-Stand

- Alle vier Plugins werden automatisch erkannt, validiert und vollständig neu gebaut.
- Für jedes Plugin werden eine `.mhplugin`-Datei und eine `.sha256`-Prüfsumme erzeugt.
- Der Plugin-Katalog wird beim Build automatisch aus den aktuellen Manifesten aktualisiert.
