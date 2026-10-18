import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def media_info():
    from services.agent.models import MediaInfo
    return MediaInfo(path="C:/media/test.mp4", duration=10, width=640, height=360,
                     fps=25, video_codec="h264", has_audio=True, size_bytes=100)
