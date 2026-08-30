# MediaHub Speech-to-Text

Lokales Speech-to-Text-Plugin für MediaHub AI-Node und Windows Compute Node.

## Funktion

Das Plugin stellt den Job-Typ `speech_to_text` bereit und verwendet eine isolierte Laufzeit mit `faster-whisper`.

## Zielplattformen

- Raspberry Pi / Linux ARM64
- Windows Compute Node / Windows AMD64

## Ausführung

Die Laufzeit wird pluginbezogen isoliert bereitgestellt. Abhängigkeiten werden nicht in die zentrale MediaHub- bzw. AI-Node-Python-Umgebung installiert.
