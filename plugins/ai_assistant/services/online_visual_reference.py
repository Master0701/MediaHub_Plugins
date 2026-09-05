from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from services.agents.frame_agent import FrameAgent
from services.visual_fingerprint import similarity


class OnlineVisualReferenceMatcher:
    """Vergleicht lokale Videoframes mit öffentlichen Referenzbildern.

    Es werden keine lokalen Video- oder Audiodaten übertragen.
    Ausschließlich das öffentliche Referenzbild wird heruntergeladen
    und anschließend lokal verarbeitet.
    """

    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"

    def __init__(
        self,
        *,
        timeout: float = 20.0,
    ):
        self.timeout = max(1.0, float(timeout))

    def tmdb_reference_url(
        self,
        raw: dict[str, Any] | None,
    ) -> str | None:
        raw = dict(raw or {})

        path = (
            raw.get("backdrop_path")
            or raw.get("poster_path")
        )

        if not path:
            return None

        path = str(path).strip()

        if not path:
            return None

        if not path.startswith("/"):
            path = "/" + path

        return self.TMDB_IMAGE_BASE + path

    def download_reference(
        self,
        url: str,
    ) -> bytes:
        req = urllib_request.Request(
            str(url),
            headers={
                "Accept": "image/*",
                "User-Agent": (
                    "MediaHub-KI-Assistent/"
                    "online-visual-reference"
                ),
            },
            method="GET",
        )

        try:
            with urllib_request.urlopen(
                req,
                timeout=self.timeout,
            ) as response:
                return response.read()

        except HTTPError as exc:
            raise RuntimeError(
                f"Referenzbild HTTP {exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Referenzbild Netzwerkfehler: {exc.reason}"
            ) from exc

    def reference_hashes(
        self,
        image_bytes: bytes,
        ffmpeg: Path,
    ) -> dict[str, str]:
        if not image_bytes:
            return {}

        suffix = ".jpg"

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as handle:
            handle.write(image_bytes)
            temp_path = Path(handle.name)

        try:
            command = [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-i",
                str(temp_path),
                "-frames:v",
                "1",
                "-vf",
                (
                    f"scale={FrameAgent.FRAME_WIDTH}:"
                    f"{FrameAgent.FRAME_HEIGHT},format=gray"
                ),
                "-f",
                "rawvideo",
                "-",
            ]

            process = subprocess.run(
                command,
                capture_output=True,
                timeout=25,
                check=False,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )

            raw = process.stdout or b""

            return FrameAgent.perceptual_hashes(raw)

        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def compare_references_to_frames(
        self,
        references: list[dict[str, Any]],
        selected_frames: list[dict[str, Any]],
        ffmpeg: Path,
    ) -> dict[str, Any]:
        """Vergleicht mehrere Online-Bildreferenzen mit lokalen Frames."""

        reference_results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for index, reference in enumerate(references, 1):
            if not isinstance(reference, dict):
                continue

            reference_url = str(
                reference.get("url") or ""
            ).strip()

            if not reference_url:
                continue

            try:
                image_bytes = self.download_reference(
                    reference_url
                )

                hashes = self.reference_hashes(
                    image_bytes,
                    ffmpeg,
                )

                if not hashes:
                    errors.append({
                        "index": index,
                        "reference_url": reference_url,
                        "error": "Keine Referenz-Hashes erzeugt.",
                    })
                    continue

                comparison = self.compare_reference_to_frames(
                    hashes,
                    selected_frames,
                )

                comparison["reference_index"] = index
                comparison["reference_url"] = reference_url
                comparison["file_path"] = reference.get(
                    "file_path"
                )
                comparison["width"] = reference.get("width")
                comparison["height"] = reference.get("height")
                comparison["vote_average"] = reference.get(
                    "vote_average"
                )
                comparison["vote_count"] = reference.get(
                    "vote_count"
                )

                reference_results.append(comparison)

            except Exception as exc:
                errors.append({
                    "index": index,
                    "reference_url": reference_url,
                    "error": str(exc),
                })

        if not reference_results:
            return {
                "executed": False,
                "reference_count": 0,
                "requested_reference_count": len(references),
                "frame_count": len(selected_frames),
                "best_similarity": 0.0,
                "strongest_three_average": 0.0,
                "reference_top_three_average": 0.0,
                "references": [],
                "errors": errors,
                "reason": (
                    "Keine Online-Bildreferenz konnte "
                    "ausgewertet werden."
                ),
            }

        reference_results.sort(
            key=lambda item: (
                float(
                    item.get(
                        "strongest_three_average"
                    )
                    or 0.0
                ),
                float(
                    item.get("best_similarity")
                    or 0.0
                ),
            ),
            reverse=True,
        )

        best_reference = reference_results[0]

        strongest_reference_scores = [
            float(
                item.get(
                    "strongest_three_average"
                )
                or 0.0
            )
            for item in reference_results[:3]
        ]

        reference_top_three_average = round(
            sum(strongest_reference_scores)
            / len(strongest_reference_scores),
            4,
        )

        return {
            "executed": True,
            "reference_count": len(reference_results),
            "requested_reference_count": len(references),
            "frame_count": len(selected_frames),

            # Kompatibel mit dem bisherigen Einzelbild-Ergebnis:
            # Bestwert und Frame-Top-3 stammen vom besten Backdrop.
            "best_similarity": float(
                best_reference.get("best_similarity")
                or 0.0
            ),
            "strongest_three_average": float(
                best_reference.get(
                    "strongest_three_average"
                )
                or 0.0
            ),

            # Neuer robuster Multi-Backdrop-Wert:
            "reference_top_three_average":
                reference_top_three_average,

            "best_reference": best_reference,
            "references": reference_results,
            "errors": errors,
        }


    def compare_reference_to_frames(
        self,
        reference_hashes: dict[str, str],
        selected_frames: list[dict[str, Any]],
    ) -> dict[str, Any]:
        comparisons = []

        for frame in selected_frames:
            hashes = dict(
                frame.get("perceptual_hashes") or {}
            )

            dhash_score = similarity(
                reference_hashes.get("dhash"),
                hashes.get("dhash"),
            )

            center_score = similarity(
                reference_hashes.get("center_dhash"),
                hashes.get("center_dhash"),
            )

            score = round(
                (dhash_score * 0.65)
                + (center_score * 0.35),
                4,
            )

            comparisons.append(
                {
                    "second": frame.get("second"),
                    "dhash_similarity": dhash_score,
                    "center_similarity": center_score,
                    "similarity": score,
                }
            )

        comparisons.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        strongest = comparisons[:3]

        strongest_score = (
            sum(
                item["similarity"]
                for item in strongest
            )
            / len(strongest)
            if strongest
            else 0.0
        )

        return {
            "schema_version": 1,
            "frame_count": len(comparisons),
            "best_similarity": (
                comparisons[0]["similarity"]
                if comparisons
                else 0.0
            ),
            "strongest_three_average": round(
                strongest_score,
                4,
            ),
            "comparisons": comparisons,
        }
