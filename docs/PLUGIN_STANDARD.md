# MediaHub Plugin-Standard

## Grundsatz

Jedes Plugin ist unabhängig installierbar, aktualisierbar und entfernbar. Gemeinsame Komponenten dürfen geteilt werden, ohne ein anderes Plugin vorauszusetzen.

## Pflichtbestandteile

Jeder Plugin-Ordner enthält mindestens:

- `plugin.json`
- Entry-Point-Datei
- `README.md`
- `CHANGELOG.md`
- `help/`
- `assets/`

## Lebenszyklus

Ein ausführbares Plugin unterstützt:

1. Laden
2. Initialisieren
3. Starten
4. Statusabfrage
5. Stoppen
6. Freigeben

## Sicherheitsregeln

- Kein Plugin greift direkt auf interne Fenster oder Manager zu.
- Zugriff erfolgt ausschließlich über die freigegebene Plugin-API.
- Berechtigungen stehen im Manifest.
- Netzwerkfunktionen müssen ihren Geltungsbereich erklären.
- WebRemote und MobileDashboard laufen standardmäßig nur lokal.
- Installationspakete werden später mit SHA-256 geprüft.

## Versionierung

- MediaHub besitzt eine eigene Version.
- Jedes Plugin besitzt eine eigene Version.
- Gemeinsame Laufzeiten besitzen eine eigene Version.
- Das Manifest nennt die minimale MediaHub-Version.

## Paketformat

Fertige Plugins werden als `.mhplugin` gebaut. Das Paket enthält nur das jeweilige Plugin und die gemeinsamen Komponenten, die es selbst zum Start benötigt.


## Kompatibilität und Veröffentlichung

- Neue Plugins setzen derzeit mindestens MediaHub `1.0.3` voraus.
- Die tatsächlich laufende MediaHub-Version kommt aus der Plugin-API und damit indirekt aus `src/mediahub/app_info.py`.
- Plugin-Version und MediaHub-Version bleiben getrennt.
- Ein Plugin-Build darf lokal ohne Passwort erstellt und getestet werden.
- Erst der Veröffentlichungsschritt zu GitHub benötigt die Passwort-/Einmalcode-Freigabe.
- Build-Pakete dürfen keine `__pycache__`-Ordner oder `.pyc`-Dateien enthalten.
