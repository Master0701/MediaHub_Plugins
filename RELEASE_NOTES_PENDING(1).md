# MediaHub Plugins – Release v0.13.5

## Enthaltene Plugins

### MediaHub WebRemote v0.13.5

- Desktop-Weboberfläche für den lokalen PC-Betrieb
- feste linke Navigation
- Dashboard, Assistent, Kanäle, Playlists, Bibliothek und Live-Downloads
- Jobs, Scheduler, Statistiken und Plugin-Übersicht
- gemeinsame WebRuntime mit Mobile Dashboard
- Desktop-Route unter `/`
- funktioniert allein oder gemeinsam mit Mobile Dashboard

### MediaHub Mobile Dashboard v0.1.5

- mobile Oberfläche für Handy und Tablet
- einklappbare linke Sidebar
- QR-Code und Gerätekopplung
- mobile Route unter `/mobile`
- funktioniert allein oder gemeinsam mit WebRemote
- bei alleiniger Installation wird die mobile Oberfläche zusätzlich direkt unter `/` ausgeliefert
- bleibt nach Stoppen oder Entfernen von WebRemote erreichbar

## Gemeinsame Änderungen

- Desktop- und Mobile-Oberfläche sauber getrennt
- gemeinsame Runtime für beide Plugins
- beide Plugins bleiben unabhängig installierbar
- gemeinsame Serverinstanz ohne Portkonflikt
- Routing und Plugin-Lebenszyklus korrigiert
- Build erzeugt für beide Plugins `.mhplugin` und `.sha256`
