# Hilfe – Metadata Editor

## Öffnen

Nach dem Start ist der Editor unter `/metadata-editor` auf derselben lokalen
Adresse wie WebRemote und Mobile Dashboard erreichbar.

## Arbeiten mit Metadaten

1. Links einen Bibliothekseintrag auswählen.
2. Gewünschte Felder ändern.
3. Mit **Änderungen prüfen** die alten und neuen Werte vergleichen.
4. Mit **Entwurf speichern** die Änderung lokal sichern.

## Endgültig speichern

Der Button bleibt deaktiviert, bis das MediaHub-Hauptprogramm die freigegebene
Plugin-Aktion `metadata.update` bereitstellt. Dadurch kann das Plugin keine
NFO-Datei oder Datenbank außerhalb der kontrollierten MediaHub-API verändern.

## Entwürfe

Entwürfe werden im MediaHub-Datenordner unter
`plugin_data/metadata_editor/drafts.json` gespeichert.
