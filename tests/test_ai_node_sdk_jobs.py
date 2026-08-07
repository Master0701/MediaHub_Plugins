from __future__ import annotations

import pytest

from shared.ai_node_sdk import (
    InvalidJobStateError,
    JobQueue,
    JobStatus,
    TaskRequest,
    TaskResult,
)


def test_job_lifecycle_queue_running_completed():
    queue = JobQueue()

    created = queue.submit(
        TaskRequest(
            task_type="test_provider",
            payload={"value": "Job"},
        )
    )

    assert created.status is JobStatus.QUEUED
    assert created.progress == 0

    running = queue.claim_next(
        node_id="pi-01",
        worker_id="worker-1",
    )

    assert running is not None
    assert running.job_id == created.job_id
    assert running.status is JobStatus.RUNNING
    assert running.node_id == "pi-01"

    progress = queue.update_progress(
        created.job_id,
        42,
        message="Analyse läuft",
    )

    assert progress.progress == 42
    assert progress.message == "Analyse läuft"

    completed = queue.complete(
        created.job_id,
        TaskResult.success(
            {"value": "fertig"},
            backend="provider.mediahub_test",
        ),
    )

    assert completed.status is JobStatus.COMPLETED
    assert completed.progress == 100
    assert completed.result is not None
    assert completed.result.ok is True


def test_cancel_queued_job():
    queue = JobQueue()
    created = queue.submit(
        TaskRequest(task_type="ocr")
    )

    cancelled = queue.cancel(created.job_id)

    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.terminal is True
    assert queue.claim_next(node_id="pi-01") is None


def test_failed_job_keeps_error_result():
    queue = JobQueue()
    created = queue.submit(
        TaskRequest(task_type="test_provider")
    )
    queue.claim_next(node_id="pi-02")

    failed = queue.fail(
        created.job_id,
        "Testfehler",
        backend="provider.mediahub_test",
    )

    assert failed.status is JobStatus.FAILED
    assert failed.result is not None
    assert failed.result.ok is False
    assert failed.result.error == "Testfehler"


def test_progress_requires_running_job():
    queue = JobQueue()
    created = queue.submit(
        TaskRequest(task_type="test_provider")
    )

    with pytest.raises(InvalidJobStateError):
        queue.update_progress(created.job_id, 10)


def test_progress_range_is_enforced():
    queue = JobQueue()
    created = queue.submit(
        TaskRequest(task_type="test_provider")
    )
    queue.claim_next(node_id="pi-03")

    with pytest.raises(ValueError):
        queue.update_progress(created.job_id, 101)


def test_multiple_nodes_claim_different_jobs():
    queue = JobQueue()

    first = queue.submit(
        TaskRequest(task_type="test_provider")
    )
    second = queue.submit(
        TaskRequest(task_type="test_provider")
    )

    claimed_a = queue.claim_next(node_id="pi-a")
    claimed_b = queue.claim_next(node_id="pi-b")

    assert claimed_a is not None
    assert claimed_b is not None
    assert claimed_a.job_id == first.job_id
    assert claimed_b.job_id == second.job_id
    assert claimed_a.node_id == "pi-a"
    assert claimed_b.node_id == "pi-b"


def test_terminal_cleanup():
    queue = JobQueue()

    one = queue.submit(TaskRequest(task_type="a"))
    two = queue.submit(TaskRequest(task_type="b"))

    queue.cancel(one.job_id)
    queue.claim_next(node_id="pi-01")
    queue.complete(
        two.job_id,
        TaskResult.success(),
    )

    assert queue.clear_terminal() == 2
    assert queue.list() == ()
