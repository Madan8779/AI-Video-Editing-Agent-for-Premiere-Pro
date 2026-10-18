import os
from pathlib import Path
import pytest
from services.media.transcription import transcribe_local


def test_model_must_be_existing_local_folder(tmp_path):
    with pytest.raises(ValueError, match="model.bin"):
        transcribe_local("unused.mp4", tmp_path)


def test_real_offline_english_fixture():
    model, source = os.getenv("MADDY_TEST_MODEL"), os.getenv("MADDY_TEST_SPEECH")
    if not model or not source:
        pytest.skip("Set local model and generated English speech fixture for adapter QA")
    segments = transcribe_local(source, model, "en")
    text = " ".join(s.text.lower() for s in segments)
    assert "engine" in text and "car" in text
    assert all(s.end > s.start >= 0 for s in segments)
