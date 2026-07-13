# Ausstehende Release-Notizen

## Mobile Dashboard – Startseite im Heimnetz repariert

- Mobile Dashboard liefert bei alleiniger Installation die mobile Oberfläche direkt unter `/` aus.
- Die fehleranfällige HTML-/302-Weiterleitung nach `/mobile` wurde entfernt.
- `/mobile` bleibt weiterhin die feste mobile Adresse.
- Wenn WebRemote parallel läuft, besitzt dessen Desktop-Route auf `/` weiterhin Vorrang.
