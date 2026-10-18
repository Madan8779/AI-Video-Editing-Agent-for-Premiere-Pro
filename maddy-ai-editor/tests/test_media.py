import hashlib
import os
import sys
import threading
from pathlib import Path
import pytest
from services.media.engine import MediaEngine, run_command, Cancelled


def test_subprocess_cancellation_and_timeout():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        run_command([sys.executable, "-c", "import time; time.sleep(30)"], cancel)
    with pytest.raises(TimeoutError):
        run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.01)


@pytest.fixture
def engine():
    ffmpeg, ffprobe = os.getenv("MADDY_FFMPEG"), os.getenv("MADDY_FFPROBE")
    if not ffmpeg or not ffprobe:
        pytest.skip("Set MADDY_FFMPEG and MADDY_FFPROBE for real fixture integration tests")
    return MediaEngine(ffmpeg, ffprobe)


def test_real_fixture_probe_silence_scene_and_source_integrity(engine, tmp_path):
    source = tmp_path / "ಕನ್ನಡ fixture.mp4"
    run_command([engine.ffmpeg, "-hide_banner", "-nostdin", "-f", "lavfi", "-i",
                 "testsrc2=size=320x180:rate=25:duration=4", "-f", "lavfi", "-i",
                 "aevalsrc=if(between(t\\,1\\,2.5)\\,0\\,0.2*sin(2*PI*440*t)):s=16000:d=4",
                 "-c:v", "mpeg4", "-c:a", "aac", "-y", str(source)])
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    info = engine.probe(source)
    assert info.width == 320 and info.height == 180
    assert 3.9 < info.duration < 4.2 and info.has_audio
    silences, scenes = engine.analyze(info)
    assert any(0.9 < s.start < 1.1 and 2.4 < s.end < 2.6 for s in silences)
    assert isinstance(scenes, list)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_corrupt_video_fails(engine, tmp_path):
    file = tmp_path / "broken.mp4"
    file.write_bytes(b"invalid video")
    with pytest.raises(RuntimeError, match="MEDIA_FAILED"):
        engine.probe(file)


def test_real_scene_boundary_and_video_without_audio(engine, tmp_path):
    source = tmp_path / "scene.mp4"
    run_command([engine.ffmpeg, "-hide_banner", "-nostdin", "-f", "lavfi", "-i",
        "color=c=black:s=320x180:r=25:d=1", "-f", "lavfi", "-i",
        "color=c=white:s=320x180:r=25:d=1", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-c:v", "mpeg4", "-y", str(source)])
    info = engine.probe(source)
    assert not info.has_audio
    silences, scenes = engine.analyze(info)
    assert silences == []
    assert any(0.9 < boundary < 1.1 for boundary in scenes)
