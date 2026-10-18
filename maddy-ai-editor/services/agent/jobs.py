import json
import uuid
from pathlib import Path


class JobQueue:
    """Small persistent single-worker queue. Interrupted work is never marked complete."""
    def __init__(self, path):
        self.path = Path(path)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.jobs = loaded if isinstance(loaded, list) else []
        except (OSError, ValueError):
            self.jobs = []
        self.jobs = [j for j in self.jobs if isinstance(j, dict) and
                     all(key in j for key in ("id", "source", "preset", "status"))]
        for job in self.jobs:
            if job["status"] == "running":
                job["status"] = "interrupted"

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.jobs, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def add(self, source, preset):
        job = {"id": uuid.uuid4().hex, "source": str(Path(source).resolve(strict=True)),
               "preset": preset, "status": "queued", "message": "Waiting"}
        self.jobs.append(job)
        self.save()
        return job

    def update(self, job_id, status, message=""):
        job = next(j for j in self.jobs if j["id"] == job_id)
        job.update(status=status, message=message)
        self.save()

    def next(self):
        return next((job for job in self.jobs if job["status"] == "queued"), None)
