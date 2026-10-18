import json
from services.agent.jobs import JobQueue


def test_queue_persists_and_marks_interrupted(tmp_path):
    source = tmp_path / "source.mp4"
    source.touch()
    path = tmp_path / "jobs.json"
    queue = JobQueue(path)
    job = queue.add(source, "Car Review")
    assert queue.next()["id"] == job["id"]
    queue.update(job["id"], "running")
    recovered = JobQueue(path)
    assert recovered.jobs[0]["status"] == "interrupted"
    assert recovered.next() is None
    recovered.update(job["id"], "queued")
    assert recovered.next()["id"] == job["id"]


def test_corrupt_queue_recovers(tmp_path):
    path = tmp_path / "jobs.json"
    path.write_text("broken")
    assert JobQueue(path).jobs == []
