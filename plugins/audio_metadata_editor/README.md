# MediaHub Audio Metadata Editor v0.0.1

Erste echte Plugin-Basis. Trotz des Namens ist die interne Architektur für
allgemeine Audiodateien ausgelegt.

## Fest vorbereitete Schnittstelle

`mediahub.audio_metadata.v1`

Operationen: `status`, `inspect`, `identify`, `compare`, `plan_write`,
`apply_write`.

Diese Schnittstelle soll später unverändert vom Metadata Editor und vom
KI-Assistenten genutzt werden.

## Tool-Vorbereitung

Bereits im Manifest vorgemerkt:

- FFmpeg / ffprobe: MediaHub-Core-Tools
- MediaInfo: vorhandenes optionales Tool
- Chromaprint / fpcalc: vorbereitet für Audio-Fingerprints
- Mp3tag: vorbereitet als optionales manuelles Expertentool

Es werden in v0.0.1 **keine Drittanbieter-Binaries mitgeliefert**.
`chromaprint_fpcalc` und `mp3tag` müssen später zusätzlich im zentralen
MediaHub Tool Manager registriert werden. Dafür liegen Vorbereitungsdateien
unter `integration/`.

## Sicherheit

Noch kein automatisches Schreiben von Audio-Tags. Die spätere Write-API ist
bereits auf Vorschau, Bestätigung, Backup und Rückleseprüfung ausgelegt.
