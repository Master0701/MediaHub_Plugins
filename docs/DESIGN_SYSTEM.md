# MediaHub Design-System

## Ziel

Alle Bestandteile der MediaHub Suite sollen wie eine zusammengehörige Anwendung wirken. Das gilt für das Hauptprogramm, WebRemote, MobileDashboard, MetadataEditor, AIAssistant und SmartRenamer.

## Gemeinsame Regeln

- Farben werden ausschließlich über zentrale Design-Tokens verwendet.
- Buttons, Karten, Tabellen, Statusanzeigen und Navigation folgen denselben Abständen und Zuständen.
- Desktop, Tablet und Handy verwenden dieselben Begriffe und Symbole.
- Plugin-spezifische Sonderfarben sind nur erlaubt, wenn sie eine fachliche Bedeutung haben.
- Barrierearme Kontraste und deutlich sichtbare Fokuszustände sind Pflicht.

## Zentrale Dateien

- `shared/mediahub_design/tokens.json`: maschinenlesbare Designwerte
- `shared/mediahub_design/mediahub-theme.css`: gemeinsames Web-Theme

## Statusfarben

- Erfolg: abgeschlossen, verbunden, aktiv
- Warnung: Aufmerksamkeit erforderlich
- Fehler: Aktion fehlgeschlagen
- Information: neutraler Hinweis
- Primärfarbe: auswählbare Hauptaktion

## Responsive Grundregel

Die Oberfläche wird nicht für ein einzelnes Gerät entworfen. Sie passt sich an:

- Desktop: feste Sidebar, mehrere Karten nebeneinander
- Tablet: schmalere Sidebar oder einklappbare Navigation
- Handy: untere Navigation oder Menüschaltfläche, Karten untereinander

MobileDashboard ergänzt später mobile Komfortfunktionen, nutzt aber dieselbe API und dieselben Komponenten wie WebRemote.
