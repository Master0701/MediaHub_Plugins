from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class SpeechRecognitionAgent:
    """Lokale Spracherkennung als Identitätsevidenz.

    Der Agent entscheidet niemals selbst über Film, Serie oder Episode.
    Er liefert ausschließlich transkribierte Evidenz für die nachgelagerte
    MediaHub-Entscheidungslogik.
    """

    DEFAULT_SAMPLE_DURATION = 60.0
    MAX_SAMPLES = 4

    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        worker_provider: Any = None,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.worker_provider = worker_provider
        self._model = None

    @staticmethod
    def available() -> bool:
        return (
            importlib.util.find_spec(
                "faster_whisper"
            )
            is not None
        )

    def status(self) -> dict[str, Any]:
        available = self.available()

        return {
            "id": "speech_recognition",
            "available": available,
            "provider": (
                "local_faster_whisper"
                if available
                else None
            ),
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "reason": (
                ""
                if available
                else
                "Python-Paket faster-whisper "
                "ist nicht verfügbar."
            ),
        }

    def _load_model(self):
        if self._model is not None:
            return self._model

        if not self.available():
            return None

        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )

        return self._model

    @classmethod
    def _sample_points(
        cls,
        duration: float,
    ) -> list[float]:

        if duration <= 0:
            return [0.0]

        # Früher Dialog/Vorspann ist für Serienidentität
        # besonders wertvoll. Danach folgen verteilte
        # Handlungspunkte.
        candidates = [
            60.0,
            300.0,
            duration * 0.40,
            duration * 0.70,
        ]

        result: list[float] = []

        for point in candidates:
            point = max(
                0.0,
                min(
                    float(point),
                    max(
                        0.0,
                        duration
                        - cls.DEFAULT_SAMPLE_DURATION,
                    ),
                ),
            )

            point = round(point, 2)

            if point not in result:
                result.append(point)

        return result[:cls.MAX_SAMPLES]

    @staticmethod
    def _extract_audio(
        file_path: Path,
        ffmpeg: Path,
        start: float,
        duration: float,
        output: Path,
    ) -> None:

        command = [
            str(ffmpeg),
            "-hide_banner",
            "-nostdin",
            "-y",
            "-v",
            "error",
            "-ss",
            str(start),
            "-i",
            str(file_path),
            "-t",
            str(duration),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )

        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip()
                or "FFmpeg-Audioextraktion fehlgeschlagen."
            )

    @staticmethod
    def _identity_terms(
        text: str,
    ) -> list[str]:
        """Extrahiert nur mögliche Identitätshinweise.

        Dies ist absichtlich keine Medienentscheidung.
        """

        if not text:
            return []

        # Großgeschriebene Abkürzungen wie NCIS, FBI usw.
        abbreviations = re.findall(
            r"\b[A-ZÄÖÜ]{2,10}\b",
            text,
        )

        # Mehrfach vorkommende Begriffe sind besonders
        # interessant. Originalschreibweise beibehalten.
        words = re.findall(
            r"\b[\wÄÖÜäöüß'-]{3,}\b",
            text,
            flags=re.UNICODE,
        )

        counts: dict[str, int] = {}
        originals: dict[str, str] = {}

        for word in words:
            key = word.casefold()
            counts[key] = counts.get(key, 0) + 1
            originals.setdefault(key, word)

        repeated = [
            originals[key]
            for key, count in counts.items()
            if count >= 2
        ]

        result: list[str] = []

        for value in [
            *abbreviations,
            *repeated,
        ]:
            value = value.strip()

            if (
                value
                and value.casefold()
                not in {
                    item.casefold()
                    for item in result
                }
            ):
                result.append(value)

        return result[:40]

    def _run_remote(
        self,
        file_path: Path,
    ) -> dict[str, Any] | None:
        provider = self.worker_provider

        if provider is None:
            return None

        execute = getattr(
            provider,
            "execute",
            None,
        )

        if not callable(execute):
            return None

        result = execute(
            "speech_to_text",
            file_path,
            payload={
                "options": {
                    "model": self.model_name,
                    "language": "de",
                    "vad_filter": True,
                    "max_segments": 30,
                    "max_audio_seconds": 180,
                }
            },
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Speech-Worker lieferte kein gültiges Ergebnis."
            )

        output = result.get("output") or {}

        if not isinstance(output, dict):
            raise RuntimeError(
                "Speech-Worker-Ausgabe besitzt ein ungültiges Format."
            )

        state = str(
            output.get("status")
            or ""
        ).strip().lower()

        if state not in {
            "completed",
            "partial",
        }:
            job = result.get("job") or {}
            error = (
                output.get("error")
                or (
                    job.get("error")
                    if isinstance(job, dict)
                    else None
                )
                or "Remote Speech-to-Text ist fehlgeschlagen."
            )
            raise RuntimeError(str(error))

        transcription = (
            output.get("transcription")
            or {}
        )

        if not isinstance(
            transcription,
            dict,
        ):
            raise RuntimeError(
                "Speech-Worker lieferte keine gültige Transkription."
            )

        transcript = str(
            transcription.get("text")
            or ""
        ).strip()

        segments = transcription.get(
            "segments",
            [],
        )

        if not isinstance(
            segments,
            list,
        ):
            segments = []

        normalized_segments = [
            dict(item)
            for item in segments
            if isinstance(item, dict)
        ]

        identity_terms = self._identity_terms(
            transcript
        )

        execution = (
            output.get("execution")
            or transcription.get("execution")
            or {}
        )

        if not isinstance(
            execution,
            dict,
        ):
            execution = {}

        return {
            "schema_version": 1,
            "state": (
                "completed"
                if transcript
                else "partial"
            ),
            "provider": "node_worker",
            "node_id": result.get("node_id"),
            "node_name": result.get("node_name"),
            "node_type": result.get("node_type"),
            "model": transcription.get(
                "model",
                self.model_name,
            ),
            "device": execution.get(
                "backend"
            ),
            "compute_type": None,
            "sample_strategy":
                "remote_identity_speech_v1",
            "sample_points": [],
            "samples": [
                {
                    "sample_start": 0.0,
                    "sample_duration": None,
                    "language": transcription.get(
                        "language"
                    ),
                    "language_probability":
                        transcription.get(
                            "language_probability"
                        ),
                    "segments":
                        normalized_segments,
                }
            ],
            "transcript": transcript,
            "identity_terms": identity_terms,
            "decision_authority": False,
            "purpose":
                "Sprachbasierte Identitätsevidenz",
            "execution": execution,
            "truncated": bool(
                transcription.get(
                    "truncated",
                    False,
                )
            ),
            "truncation_reason":
                transcription.get(
                    "truncation_reason"
                ),
            "limits": transcription.get(
                "limits"
            ),
        }

    def run(
        self,
        file_path: Path,
        ffmpeg: Path | None,
        duration: float,
    ) -> dict[str, Any]:

        remote_error = ""

        if self.worker_provider is not None:
            try:
                remote = self._run_remote(
                    file_path
                )

                if remote is not None:
                    return remote

            except Exception as exc:
                remote_error = str(exc)

        if ffmpeg is None:
            return {
                "state": "unavailable",
                "reason": (
                    "ffmpeg wurde nicht gefunden."
                    + (
                        f" Remote Speech fehlgeschlagen: "
                        f"{remote_error}"
                        if remote_error
                        else ""
                    )
                ),
                "remote_reason": remote_error,
            }

        if not self.available():
            return {
                "state": "unavailable",
                "reason": (
                    "Lokale Speech-to-Text-Engine "
                    "faster-whisper ist nicht verfügbar."
                    + (
                        f" Remote Speech fehlgeschlagen: "
                        f"{remote_error}"
                        if remote_error
                        else ""
                    )
                ),
                "provider": "local_faster_whisper",
                "remote_reason": remote_error,
            }

        model = self._load_model()

        if model is None:
            return {
                "state": "unavailable",
                "reason": "Speech-Modell konnte nicht geladen werden.",
            }

        sample_points = self._sample_points(
            duration
        )

        samples: list[dict[str, Any]] = []
        full_text: list[str] = []

        try:
            with tempfile.TemporaryDirectory(
                prefix="mediahub_speech_"
            ) as temp_dir:

                temp = Path(temp_dir)

                for index, start in enumerate(
                    sample_points,
                    1,
                ):
                    wav = (
                        temp
                        / f"speech_{index}.wav"
                    )

                    self._extract_audio(
                        file_path,
                        ffmpeg,
                        start,
                        self.DEFAULT_SAMPLE_DURATION,
                        wav,
                    )

                    segments, info = model.transcribe(
                        str(wav),
                        language=None,
                        beam_size=5,
                        vad_filter=True,
                        vad_parameters={
                            "min_silence_duration_ms": 500,
                        },
                    )

                    transcript_segments = []

                    for segment in segments:
                        text = (
                            segment.text
                            or ""
                        ).strip()

                        if not text:
                            continue

                        transcript_segments.append(
                            {
                                "start": round(
                                    start
                                    + float(segment.start),
                                    2,
                                ),
                                "end": round(
                                    start
                                    + float(segment.end),
                                    2,
                                ),
                                "text": text,
                            }
                        )

                        full_text.append(text)

                    samples.append(
                        {
                            "sample_start": start,
                            "sample_duration":
                                self.DEFAULT_SAMPLE_DURATION,
                            "language":
                                getattr(
                                    info,
                                    "language",
                                    None,
                                ),
                            "language_probability":
                                round(
                                    float(
                                        getattr(
                                            info,
                                            "language_probability",
                                            0.0,
                                        )
                                        or 0.0
                                    ),
                                    4,
                                ),
                            "segments":
                                transcript_segments,
                        }
                    )

        except Exception as exc:
            return {
                "state": "failed",
                "provider": "local_faster_whisper",
                "reason": str(exc),
                "samples": samples,
            }

        transcript = " ".join(
            full_text
        ).strip()

        identity_terms = self._identity_terms(
            transcript
        )

        return {
            "schema_version": 1,
            "state": (
                "completed"
                if transcript
                else "partial"
            ),
            "provider": "local_faster_whisper",
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "sample_strategy":
                "targeted_identity_speech_v1",
            "sample_points": sample_points,
            "samples": samples,
            "transcript": transcript,
            "identity_terms": identity_terms,
            "decision_authority": False,
            "purpose":
                "Sprachbasierte Identitätsevidenz",
        }
