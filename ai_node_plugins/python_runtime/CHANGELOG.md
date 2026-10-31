# Changelog

## 0.1.0
- Grundstruktur fuer die gemeinsame Python-Runtime.

## 0.1.1
- Bestaetigter Python-3.12.10-Download aus MediaHub_Tools mit gepinntem SHA256, Manifestpruefung und sicherer ZIP-Installation.
- Vorhandene Runtime bleibt unveraendert; kein automatischer Download beim Plugin-Start.

## 0.1.2
- Erstinstallation erstellt fehlende private_python-Elternverzeichnisse selbst.
- Pruefung auf Junctions/Symlinks vor der Erstellung; bestehende Runtime wird nicht ueberschrieben.
