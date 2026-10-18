import secrets
import threading
import time
from pathlib import Path


class PathPolicy:
    def __init__(self, roots):
        self.roots = tuple(Path(root).resolve(strict=True) for root in roots)

    def check(self, value, *, exists=True):
        path = Path(value).expanduser().resolve(strict=exists)
        if not any(path.is_relative_to(root) for root in self.roots):
            raise PermissionError("PATH_DENIED: path is outside selected media folders")
        if exists and not path.is_file():
            raise ValueError("MEDIA_NOT_FILE")
        return path


class ApprovalStore:
    """UI-owned capabilities. Scope, payload, expiry, and one-use are checked atomically."""
    def __init__(self):
        self._tokens = {}
        self._lock = threading.Lock()

    def issue(self, operation, digest, ttl=120):
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = (operation, digest, time.monotonic() + ttl)
        return token

    def consume(self, token, operation, digest):
        with self._lock:
            grant = self._tokens.pop(token, None)
        if not grant or grant[:2] != (operation, digest) or grant[2] < time.monotonic():
            raise PermissionError("APPROVAL_REQUIRED: token expired, reused, or scope mismatch")
