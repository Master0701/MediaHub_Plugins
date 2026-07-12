# Changelog – MediaHub WebRemote

## v0.10.0
- kompletter Start-/Download-Assistent direkt im Browser
- sechs Schritte: Quelle, Ordner, Benennung, Playlists, Automatisierung, Zusammenfassung
- YouTube-Kanalinfos und Playlists werden über dieselben MediaHub-Dienste geladen
- Kanal, Job und Scheduler-Aufgabe können gespeichert werden
- optional sofort synchronisieren oder synchronisieren und Downloadauswahl öffnen
- Schreiben erfolgt weiterhin ausschließlich über die zentrale Action-Registry im Qt-Hauptthread

# WebRemote v0.10.0

- Zentrale Action-Registrierung in WebRemote und MediaHub-Plugin-API.
- Start-Assistent `setup_wizard.open` dauerhaft freigegeben.
- Aktionsnamen werden nicht mehr in mehreren Whitelists getrennt gepflegt.
- Fehlermeldungen nennen unbekannte Aktionen eindeutig.

# WebRemote v0.8.2

- Assistent-Schaltfläche öffnet jetzt den richtigen Start-/Download-Assistenten.
- Freigegebene Aktion auf `setup_wizard.open` umgestellt.
- Versions- und Katalogdaten konsistent aktualisiert.

# WebRemote v0.8.1

- Fehlende Browser-Funktion `runAction()` ergänzt.
- Schreibaktionen zeigen jetzt Bestätigung und Rückmeldung.
- Kanal-Synchronisierung übergibt den korrekten Kanalindex.

# Changelog

## 0.8.1
- Kontrollierte Schreibaktionen ergänzt.
- Kanal-Synchronisierung, Downloadsteuerung, Jobs, Scheduler, Assistent und Plugin-Center.
- Bestätigung vor jeder Aktion.

# Changelog

## 0.6.1

- Zentrale Aktionsleiste direkt im Dashboard ergänzt.
- Schnellzugriffe auf Assistent, Kanäle, Downloads und Plugins.
- Aktuelle Seite kann direkt neu geladen werden.
- Keine neue Schreibberechtigung; alle Aktionen bleiben Navigation oder Aktualisierung.

 – MediaHub WebRemote

## 0.6.0
- Vollständiger lesender Ausbau: Dashboard, Kanäle, Playlists, Bibliothek, Downloads, Jobs, Scheduler, Statistik, Plugins, System und Aktivitäten.
- Keine Steuer- oder Schreibfunktionen.
- Private Pfade und Zugangsdaten werden nicht ausgegeben.

## 0.5.3
- Live-Aktivitäten ergänzt.
