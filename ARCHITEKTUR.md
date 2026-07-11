# Architekturentscheidung

## Zwei getrennte Repositories

1. `MediaHub` – Hauptprogramm, Plugin-Schnittstelle und Plugin-Center
2. `MediaHub-Plugins` – gesamte Plugin-Produktfamilie

## Einzelne Installation

Jedes Plugin liegt in einem eigenen Ordner und wird als eigene `.mhplugin`-Datei gebaut.

## Gemeinsame Basis

`shared/mediahub_web_core` enthält den lokalen Webserver und später die gemeinsame API-Basis für WebRemote und MobileDashboard.

## Noch notwendige MediaHub-Erweiterung

Der aktuelle MediaHub-Loader kann Manifestdateien entdecken und `.mhplugin`-Archive installieren. Er lädt aber noch keinen Plugin-Code. Benötigt werden später:

- sichere Entry-Point-Auflösung
- Start/Stop-Lebenszyklus
- begrenzte MediaHub-API statt direktem Zugriff auf interne Objekte
- Aktivieren/Deaktivieren
- Deinstallation und Update
- Katalogdownload mit Prüfsumme
