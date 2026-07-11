# MediaHub Suite – Architektur

## Repositories

### MediaHub

Enthält das Hauptprogramm, das Plugin-Center, die sichere Plugin-API und den Plugin-Lebenszyklus.

### MediaHub-Plugins

Enthält die gesamte Plugin-Produktfamilie. Jedes Plugin liegt in einem eigenen Ordner und wird separat ausgeliefert.

## Schichten

```text
Browser / mobile Oberfläche
            ↓
WebRemote oder MobileDashboard
            ↓
gemeinsame lokale Web- und API-Basis
            ↓
freigegebene MediaHub Plugin-API
            ↓
MediaHub Hauptprogramm
```

Plugins greifen nicht direkt auf interne MediaHub-Klassen zu.

## Gemeinsame Basis

- `shared/mediahub_web_core` – lokaler Webserver und spätere API-Basis
- `shared/mediahub_design` – zentrale Farben, Abstände und Web-Komponenten

Plugin 1 und Plugin 2 verwenden dieselbe Basis. Beide müssen dennoch alleine installierbar und lauffähig bleiben.

## Netzwerk

WebRemote ist kein Cloud-Dienst. Es läuft ausschließlich lokal:

- zuerst nur `127.0.0.1`
- später auf Wunsch im Heimnetz
- keine Router-Portfreigabe
- kein externer Server erforderlich

## Plugin-Katalog

MediaHub soll später den Katalog dieses Repositories lesen und Plugins selbst herunterladen. Der Ablauf lautet:

1. Katalog laden
2. Kompatibilität prüfen
3. Paket herunterladen
4. SHA-256 prüfen
5. sicher entpacken
6. Plugin registrieren
7. starten oder für den nächsten Start vormerken

## Entwicklungsprinzip

Erst gemeinsame und stabile Schnittstellen bauen, danach Funktionen ergänzen. WebRemote dient als erstes Referenz-Plugin für alle späteren Plugins.


## Verbindlicher MediaHub-Kompatibilitätsstand

Die Plugin-Produktfamilie basiert ab jetzt auf **MediaHub v1.0.3**.

- Die MediaHub-Version wird ausschließlich über `src/mediahub/app_info.py` bestimmt.
- Plugin-Manifeste geben `minimum_mediahub_version` an und dürfen keine eigene Kopie der MediaHub-Version pflegen.
- Der Plugin-Release bleibt vom MediaHub-Hauptrelease getrennt.
- Vor einer späteren Veröffentlichung in GitHub wird – wie im MediaHub-Release-Assistenten – direkt vor Commit/Tag/Release eine Passwort- bzw. Einmalcode-Freigabe verlangt.
- Diese Freigabe betrifft nur die Veröffentlichung und niemals den normalen Start eines installierten Plugins.
