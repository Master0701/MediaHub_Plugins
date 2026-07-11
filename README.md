# MediaHub Plugins

Eigenständige Produktfamilie für offizielle MediaHub-Erweiterungen.

## Aufbau

- `shared/` – gemeinsame Laufzeit und Schnittstellen
- `plugins/web_remote/` – Plugin 1: lokale Web-Fernsteuerung
- `plugins/mobile_dashboard/` – Plugin 2: spätere Handy-/Tablet-Oberfläche
- `catalog/` – Metadaten für den späteren Download im MediaHub Plugin-Center
- `dist/` – gebaute `.mhplugin`-Pakete

Jedes Plugin wird getrennt gebaut, veröffentlicht, installiert und deinstalliert.
