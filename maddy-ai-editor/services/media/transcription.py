from pathlib import Path
from services.agent.models import Segment
from services.media.engine import Cancelled


def transcribe_local(source, model_path, language="en", cancel=None):
    """Explicitly selected existing model only; never downloads or uploads media."""
    model_path = Path(model_path).resolve(strict=True)
    if not (model_path / "model.bin").is_file():
        raise ValueError("Select a local CTranslate2 model folder containing model.bin")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Offline transcription adapter is not installed; see user manual") from exc
    model = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
    stream, info = model.transcribe(str(source), language=None if language == "auto" else language,
                                    beam_size=3, vad_filter=True)
    results = []
    for part in stream:
        if cancel and cancel.is_set():
            raise Cancelled("Transcription cancelled")
        text = part.text.strip()
        if text:
            results.append(Segment(start=part.start, end=part.end, text=text))
    return results
