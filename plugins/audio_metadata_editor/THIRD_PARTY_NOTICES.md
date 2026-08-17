# Third-Party Notices

v0.0.1 bundles no third-party binaries.

## FFmpeg / ffprobe
Provided by MediaHub Core. License depends on the concrete build (GPL/LGPL
and component licenses).

## MediaInfo
Optional MediaHub Tool Manager component. BSD-2-Clause.

## Chromaprint / fpcalc
Planned optional fingerprint backend. Upstream project:
https://github.com/acoustid/chromaprint

Chromaprint project code is MIT-licensed in current upstream releases, but
concrete fpcalc binaries can contain or depend on FFmpeg and therefore must
retain the license notices of the concrete binary distribution.

## Mp3tag
Planned optional manual expert tool. It is not intended as the automated
background metadata backend.

Official project:
https://www.mp3tag.de/

MediaHub should download/setup it only through the Tool Manager and must
preserve the vendor's terms. No Mp3tag binary is included here.
