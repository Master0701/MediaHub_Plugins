from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any


class FrameAgent:
    """Extrahiert kleine Graustufenbilder und bewertet deren Nutzbarkeit."""

    FRAME_WIDTH = 96
    FRAME_HEIGHT = 54
    FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT

    @staticmethod
    def _hex_bits(bits: list[bool]) -> str:
        value = 0
        for bit in bits:
            value = (value << 1) | int(bool(bit))
        width = max(1, (len(bits) + 3) // 4)
        return f"{value:0{width}x}"

    @classmethod
    def perceptual_hashes(cls, raw: bytes) -> dict[str, str]:
        """Erzeugt kleine tolerante Hashes direkt aus dem Graustufenbild."""
        if len(raw) < cls.FRAME_BYTES:
            return {}

        pixels = raw[: cls.FRAME_BYTES]
        width = cls.FRAME_WIDTH
        height = cls.FRAME_HEIGHT

        def block_average(x0: int, y0: int, x1: int, y1: int) -> float:
            values = []
            for y in range(y0, min(y1, height)):
                start = y * width
                for x in range(x0, min(x1, width)):
                    values.append(pixels[start + x])
            return sum(values) / len(values) if values else 0.0

        # 8x8 average hash.
        cell_w = width / 8
        cell_h = height / 8
        cells = []
        for y in range(8):
            for x in range(8):
                cells.append(
                    block_average(
                        round(x * cell_w),
                        round(y * cell_h),
                        round((x + 1) * cell_w),
                        round((y + 1) * cell_h),
                    )
                )
        mean = sum(cells) / len(cells)
        ahash = cls._hex_bits([value >= mean for value in cells])

        # 9x8 block grid -> 8x8 horizontal difference hash.
        grid = []
        cell_w = width / 9
        cell_h = height / 8
        for y in range(8):
            row = []
            for x in range(9):
                row.append(
                    block_average(
                        round(x * cell_w),
                        round(y * cell_h),
                        round((x + 1) * cell_w),
                        round((y + 1) * cell_h),
                    )
                )
            grid.append(row)

        dhash_bits = []
        for row in grid:
            for x in range(8):
                dhash_bits.append(row[x] > row[x + 1])

        # Zentraler 60-%-Ausschnitt für wiederkehrende Hauptmotive.
        crop_x0 = round(width * 0.20)
        crop_x1 = round(width * 0.80)
        crop_y0 = round(height * 0.18)
        crop_y1 = round(height * 0.82)
        crop_width = max(1, crop_x1 - crop_x0)
        crop_height = max(1, crop_y1 - crop_y0)

        center_grid = []
        for y in range(8):
            row = []
            for x in range(9):
                x0 = crop_x0 + round(x * crop_width / 9)
                x1 = crop_x0 + round((x + 1) * crop_width / 9)
                y0 = crop_y0 + round(y * crop_height / 8)
                y1 = crop_y0 + round((y + 1) * crop_height / 8)
                row.append(block_average(x0, y0, x1, y1))
            center_grid.append(row)

        center_bits = []
        for row in center_grid:
            for x in range(8):
                center_bits.append(row[x] > row[x + 1])

        return {
            "ahash": cls._hex_bits([value >= mean for value in cells]),
            "dhash": cls._hex_bits(dhash_bits),
            "center_dhash": cls._hex_bits(center_bits),
        }

    @classmethod
    def measure_gray_frame(cls, raw: bytes) -> dict[str, float]:
        if len(raw) < cls.FRAME_BYTES:
            return {}

        pixels = raw[: cls.FRAME_BYTES]
        values = list(pixels)
        count = len(values)
        average = sum(values) / count
        minimum = min(values)
        maximum = max(values)

        variance = sum((value - average) ** 2 for value in values) / count
        standard_deviation = math.sqrt(variance)

        gradient_total = 0
        gradient_count = 0
        width = cls.FRAME_WIDTH
        height = cls.FRAME_HEIGHT

        for y in range(height):
            row = y * width
            for x in range(width):
                index = row + x
                current = values[index]

                if x + 1 < width:
                    gradient_total += abs(current - values[index + 1])
                    gradient_count += 1
                if y + 1 < height:
                    gradient_total += abs(current - values[index + width])
                    gradient_count += 1

        sharpness = (
            gradient_total / gradient_count
            if gradient_count
            else 0.0
        )

        dark_ratio = sum(value <= 18 for value in values) / count
        bright_ratio = sum(value >= 238 for value in values) / count

        return {
            "yavg": round(average, 3),
            "ymin": float(minimum),
            "ymax": float(maximum),
            "contrast": round(maximum - minimum, 3),
            "stddev": round(standard_deviation, 3),
            "sharpness": round(sharpness, 3),
            "dark_ratio": round(dark_ratio, 4),
            "bright_ratio": round(bright_ratio, 4),
        }

    def run(
        self,
        file_path: Path,
        ffmpeg: Path | None,
        sample_points: list[float],
    ) -> dict[str, Any]:
        if ffmpeg is None:
            return {
                "state": "unavailable",
                "reason": "ffmpeg wurde nicht gefunden.",
                "samples": [],
            }

        samples: list[dict[str, Any]] = []

        for point in sample_points[:20]:
            command = [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-ss",
                str(max(0.0, float(point))),
                "-i",
                str(file_path),
                "-frames:v",
                "1",
                "-vf",
                f"scale={self.FRAME_WIDTH}:{self.FRAME_HEIGHT},format=gray",
                "-an",
                "-f",
                "rawvideo",
                "-",
            ]

            try:
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
                raw_frame = process.stdout or b""
                metrics = self.measure_gray_frame(raw_frame)
                hashes = self.perceptual_hashes(raw_frame)
                if metrics:
                    samples.append(
                        {
                            "second": round(float(point), 2),
                            "metrics": metrics,
                            "perceptual_hashes": hashes,
                        }
                    )
                else:
                    samples.append(
                        {
                            "second": round(float(point), 2),
                            "error": (
                                (process.stderr or b"")
                                .decode("utf-8", errors="replace")
                                .strip()
                                or "Kein verwertbares Videobild extrahiert."
                            ),
                        }
                    )
            except Exception as exc:
                samples.append(
                    {
                        "second": round(float(point), 2),
                        "error": str(exc),
                    }
                )

        valid = [item for item in samples if item.get("metrics")]
        averages: dict[str, float] = {}

        for key in (
            "yavg",
            "contrast",
            "stddev",
            "sharpness",
            "dark_ratio",
            "bright_ratio",
        ):
            values = [
                float(item["metrics"][key])
                for item in valid
                if key in item["metrics"]
            ]
            if values:
                averages[key] = round(sum(values) / len(values), 3)

        return {
            "schema_version": 4,
            "state": "completed" if valid else "failed",
            "sample_count": len(valid),
            "requested_sample_count": min(len(sample_points), 20),
            "samples": samples,
            "averages": averages,
            "purpose": (
                "Helligkeit, Kontrast, Bildinhalt und lokale "
                "Schärfe geeigneter Videoframes"
            ),
        }
