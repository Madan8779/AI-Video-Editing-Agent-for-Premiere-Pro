import json
import threading
from pathlib import Path
from apps.desktop.main import MainWindow, Worker, load_settings
from services.agent.models import Preset, create_plan
from services.media.engine import MediaEngine


def test_desktop_import_review_and_json_validation(qt_app, tmp_path, media_info):
    source = tmp_path / "test.mp4"
    source.touch()
    window = MainWindow(tmp_path / "settings.json", start_bridge=False)
    window.show()
    qt_app.processEvents()
    assert not window.analyze_button.isEnabled()
    window.set_source(source)
    assert window.analyze_button.isEnabled()
    info = media_info.model_copy(update={"path": str(source)})
    plan = create_plan(info, [], Preset.CAR)
    window.on_result((info, [], [], plan, []))
    assert window.table.rowCount() == 1
    assert window.current_plan().source_path == str(source)
    window.table.item(0, 1).setText("8.000")
    assert window.current_plan().output_duration == 8
    window.close()


def test_worker_reports_missing_tool_without_false_success(tmp_path):
    source = tmp_path / "a.mp4"
    source.touch()
    engine = MediaEngine("missing-ffmpeg", "missing-ffprobe")
    worker = Worker(engine, source, Preset.CAR, threading.Event())
    errors, results, done = [], [], []
    worker.failed.connect(errors.append)
    worker.result.connect(results.append)
    worker.done.connect(lambda: done.append(True))
    worker.run()
    assert errors and "FFPROBE_MISSING" in errors[0]
    assert not results and done


def test_corrupt_settings_recovers(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text("broken")
    assert load_settings(file) == {}
    file.write_text(json.dumps({"model": "local-model"}), encoding="utf-8-sig")
    assert load_settings(file)["model"] == "local-model"


def test_actual_threaded_queue_finishes_and_saves_plans(qt_app, tmp_path):
    import os
    import time
    import pytest
    from PySide6.QtTest import QTest
    from services.media.engine import run_command
    ffmpeg, ffprobe = os.getenv("MADDY_FFMPEG"), os.getenv("MADDY_FFPROBE")
    if not ffmpeg or not ffprobe:
        pytest.skip("Configure FFmpeg to exercise actual threaded jobs")
    source = tmp_path / "source.mp4"
    run_command([ffmpeg, "-hide_banner", "-nostdin", "-f", "lavfi", "-i",
                 "color=c=blue:s=320x180:r=25:d=1", "-c:v", "mpeg4", "-y", str(source)])
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"ffmpeg": ffmpeg, "ffprobe": ffprobe}))
    window = MainWindow(settings, start_bridge=False)
    window.queue.add(source, "Car Review")
    window.queue.add(source, "Travel Vlog")
    window.refresh_queue()
    window.run_queue()
    deadline = time.monotonic() + 20
    while (window.thread or window.queue_running) and time.monotonic() < deadline:
        QTest.qWait(30)
    assert window.thread is None and not window.queue_running
    assert [job["status"] for job in window.queue.jobs] == ["complete", "complete"]
    assert len(list((tmp_path / "plans").glob("*.json"))) == 2
    window.close()
