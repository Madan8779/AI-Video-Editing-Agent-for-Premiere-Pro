"""Bounded subprocess media analysis. No shell and no source writes."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from fractions import Fraction
from pathlib import Path
from services.agent.models import MediaInfo, Span


class Cancelled(Exception):
    pass


def run_command(args, cancel=None, timeout=1800):
    cancel = cancel or threading.Event()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Disk-backed output prevents deadlocks and unbounded in-memory pipe buffers.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(args, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                   creationflags=flags, shell=False)
        started = time.monotonic()
        try:
            while process.poll() is None:
                if cancel.wait(0.08):
                    raise Cancelled("Job cancelled; source preserved")
                if time.monotonic() - started > timeout:
                    raise TimeoutError("MEDIA_TIMEOUT")
                if stdout.tell() + stderr.tell() > 32 * 1024 * 1024:
                    raise RuntimeError("MEDIA_OUTPUT_LIMIT")
            stdout.seek(0)
            stderr.seek(0)
            out = stdout.read(32 * 1024 * 1024).decode("utf-8", "replace")
            err = stderr.read(32 * 1024 * 1024).decode("utf-8", "replace")
            if process.returncode:
                raise RuntimeError("MEDIA_FAILED: " + err[-1500:])
            return out, err
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


class MediaEngine:
    def __init__(self, ffmpeg="", ffprobe=""):
        self.ffmpeg = ffmpeg or shutil.which("ffmpeg") or ""
        self.ffprobe = ffprobe or shutil.which("ffprobe") or ""

    def tools(self):
        return {"ffmpeg": bool(self.ffmpeg and Path(self.ffmpeg).is_file()),
                "ffprobe": bool(self.ffprobe and Path(self.ffprobe).is_file())}

    def probe(self, path, cancel=None):
        if not self.tools()["ffprobe"]:
            raise FileNotFoundError("FFPROBE_MISSING: configure ffprobe.exe in Settings")
        path = Path(path).resolve(strict=True)
        if path.suffix.lower() not in (".mp4", ".mov", ".mkv", ".avi", ".webm"):
            raise ValueError("UNSUPPORTED_MEDIA: select MP4, MOV, MKV, AVI or WebM")
        output, _ = run_command([self.ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe",
                                  "-show_format", "-show_streams", "-of", "json", str(path)], cancel, 60)
        data = json.loads(output)
        video = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), None)
        if not video:
            raise ValueError("NO_VIDEO_STREAM")
        fps = video.get("avg_frame_rate", "0/0")
        if fps in ("0/0", "0"):
            fps = video.get("r_frame_rate", "0/0")
        return MediaInfo(path=str(path), duration=float(data["format"]["duration"]),
                         width=video["width"], height=video["height"], fps=float(Fraction(fps)),
                         video_codec=video["codec_name"],
                         has_audio=any(s["codec_type"] == "audio" for s in data["streams"]),
                         size_bytes=path.stat().st_size)

    def analyze(self, info, cancel=None, progress=lambda n, message: None):
        if not self.tools()["ffmpeg"]:
            raise FileNotFoundError("FFMPEG_MISSING: configure ffmpeg.exe in Settings")
        progress(15, "Detecting silent intervals locally")
        silences = []
        common = [self.ffmpeg, "-hide_banner", "-nostdin", "-protocol_whitelist", "file,pipe", "-i", info.path]
        if info.has_audio:
            _, log = run_command(common + ["-vn", "-af", "silencedetect=noise=-35dB:d=0.7",
                                           "-f", "null", "-"], cancel)
            start = None
            for match in re.finditer(r"silence_(start|end):\s*([0-9.]+)", log):
                value = min(float(match[2]), info.duration)
                if match[1] == "start":
                    start = value
                elif start is not None and value > start:
                    silences.append(Span(start=start, end=value))
                    start = None
            if start is not None and info.duration > start:
                silences.append(Span(start=start, end=info.duration))
        progress(55, "Detecting scene boundaries locally")
        _, log = run_command(common + ["-an", "-vf", "scale=320:-2,select='gt(scene,0.35)',showinfo",
                                       "-fps_mode", "vfr", "-f", "null", "-"], cancel)
        scenes = sorted(set(float(v) for v in re.findall(r"pts_time:([0-9.]+)", log)))
        progress(95, "Preparing editable cut suggestions")
        return silences, scenes
