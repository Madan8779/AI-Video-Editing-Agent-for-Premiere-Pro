"""Generate a disposable media fixture; never reads production footage."""
import json
import os
from pathlib import Path
from services.media.engine import run_command

root = Path(__file__).resolve().parents[1]
output = root / "samples" / "generated"
output.mkdir(parents=True, exist_ok=True)
ffmpeg, ffprobe = os.environ["MADDY_FFMPEG"], os.environ["MADDY_FFPROBE"]
run_command([ffmpeg, "-hide_banner", "-nostdin", "-f", "lavfi", "-i",
             "testsrc2=size=640x360:rate=25:duration=8", "-f", "lavfi", "-i",
             "aevalsrc=if(between(t\\,2\\,5)\\,0\\,0.2*sin(2*PI*440*t)):s=16000:d=8",
             "-c:v", "mpeg4", "-c:a", "aac", "-y", str(output / "review-fixture.mp4")])
artifacts = root / "artifacts"
artifacts.mkdir(exist_ok=True)
(artifacts / "settings.json").write_text(json.dumps({"ffmpeg": ffmpeg, "ffprobe": ffprobe,
                                                       "onboarded": True}, indent=2), encoding="utf-8")
print(output / "review-fixture.mp4")
