from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from threading import RLock
from typing import Iterable

from .job import Job, JobStatus
from .task import TaskRequest, TaskResult


class JobNotFoundError(KeyError):
    pass


class InvalidJobStateError(RuntimeError):
    pass


class JobQueue:
    """
    Thread-sichere In-Memory-Jobverwaltung.

    Sie startet selbst keine Hintergrundthreads und führt keine Aufgaben aus.
    Ein AI-Node-Worker bzw. Orchestrator claimt Jobs explizit und meldet
    Fortschritt/Ergebnis zurück.
    """

    def __init__(self) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = RLock()

    def submit(self, request: TaskRequest) -> Job:
        job = Job(request=request)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            try:
                return self._jobs[job_id]
            except KeyError as exc:
                raise JobNotFoundError(job_id) from exc

    def list(
        self,
        *,
        statuses: Iterable[JobStatus] | None = None,
    ) -> tuple[Job, ...]:
        with self._lock:
            jobs = tuple(self._jobs.values())

        if statuses is None:
            return jobs

        wanted = set(statuses)
        return tuple(job for job in jobs if job.status in wanted)

    def claim_next(
        self,
        *,
        node_id: str,
        worker_id: str = "",
    ) -> Job | None:
        node = str(node_id).strip()
        if not node:
            raise ValueError("node_id darf nicht leer sein.")

        with self._lock:
            for job_id, job in self._jobs.items():
                if job.status is not JobStatus.QUEUED:
                    continue

                updated = job.with_update(
                    status=JobStatus.RUNNING,
                    progress=max(job.progress, 0),
                    node_id=node,
                    worker_id=str(worker_id).strip(),
                )
                self._jobs[job_id] = updated
                return updated

        return None

    def update_progress(
        self,
        job_id: str,
        progress: int,
        *,
        message: str = "",
    ) -> Job:
        value = int(progress)
        if value < 0 or value > 100:
            raise ValueError("Fortschritt muss zwischen 0 und 100 liegen.")

        with self._lock:
            job = self.get(job_id)

            if job.status is not JobStatus.RUNNING:
                raise InvalidJobStateError(
                    "Fortschritt kann nur für laufende Jobs geändert werden."
                )

            updated = job.with_update(
                progress=value,
                message=str(message),
            )
            self._jobs[job_id] = updated
            return updated

    def complete(
        self,
        job_id: str,
        result: TaskResult,
        *,
        message: str = "",
    ) -> Job:
        with self._lock:
            job = self.get(job_id)

            if job.status is not JobStatus.RUNNING:
                raise InvalidJobStateError(
                    "Nur laufende Jobs können abgeschlossen werden."
                )

            updated = job.with_update(
                status=JobStatus.COMPLETED,
                progress=100,
                message=str(message),
                result=result,
            )
            self._jobs[job_id] = updated
            return updated

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        backend: str = "",
        message: str = "",
    ) -> Job:
        with self._lock:
            job = self.get(job_id)

            if job.status is not JobStatus.RUNNING:
                raise InvalidJobStateError(
                    "Nur laufende Jobs können als fehlgeschlagen markiert werden."
                )

            result = TaskResult.failure(
                str(error),
                backend=str(backend),
                metadata={
                    "request_id": job.request.request_id,
                    "job_id": job.job_id,
                },
            )

            updated = job.with_update(
                status=JobStatus.FAILED,
                message=str(message) or str(error),
                result=result,
            )
            self._jobs[job_id] = updated
            return updated

    def cancel(
        self,
        job_id: str,
        *,
        message: str = "Abgebrochen.",
    ) -> Job:
        with self._lock:
            job = self.get(job_id)

            if job.terminal:
                return job

            updated = job.with_update(
                status=JobStatus.CANCELLED,
                message=str(message),
            )
            self._jobs[job_id] = updated
            return updated

    def remove_terminal(self, job_id: str) -> Job:
        with self._lock:
            job = self.get(job_id)
            if not job.terminal:
                raise InvalidJobStateError(
                    "Nur abgeschlossene Jobs dürfen entfernt werden."
                )
            return self._jobs.pop(job_id)

    def clear_terminal(self) -> int:
        with self._lock:
            remove_ids = [
                job_id
                for job_id, job in self._jobs.items()
                if job.terminal
            ]
            for job_id in remove_ids:
                del self._jobs[job_id]
            return len(remove_ids)
