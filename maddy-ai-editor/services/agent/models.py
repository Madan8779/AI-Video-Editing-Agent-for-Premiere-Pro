"""Shared strict contracts. All ranges use source seconds, end exclusive."""
import hashlib
import json
import math
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Preset(str, Enum):
    CAR = "Car Review"
    TRAVEL = "Travel Vlog"
    EDUCATION = "Educational Video"
    SHORTS = "Shorts"


class MediaInfo(StrictModel):
    path: str
    duration: float = Field(gt=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    fps: float = Field(gt=0)
    video_codec: str
    has_audio: bool
    size_bytes: int = Field(ge=0)


class Span(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("Range end must follow start")
        return self


class Segment(Span):
    text: str = Field(min_length=1, max_length=10000)


class Cut(Span):
    rationale: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class EditPlan(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    source_path: str
    source_duration: float = Field(gt=0)
    preset: Preset
    fps: float = Field(gt=0)
    keeps: list[Cut] = Field(min_length=1, max_length=10000)
    strategy: str = "Review source ranges before manual EDL import; originals are preserved."

    @model_validator(mode="after")
    def valid_ranges(self):
        last = 0.0
        for cut in self.keeps:
            if cut.start < last or cut.end > self.source_duration + 0.000001:
                raise ValueError("Ranges overlap, are unsorted, or exceed source duration")
            last = cut.end
        return self

    @property
    def output_duration(self):
        return sum(c.end - c.start for c in self.keeps)

    def digest(self):
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


def create_plan(info: MediaInfo, silences: list[Span], preset: Preset) -> EditPlan:
    """Conservative silence suggestions. Never classify semantic quality as AI judgment."""
    padding = {Preset.CAR: 0.25, Preset.TRAVEL: 0.4,
               Preset.EDUCATION: 0.3, Preset.SHORTS: 0.15}[preset]
    keeps, cursor = [], 0.0
    for silence in sorted(silences, key=lambda s: s.start):
        start = min(info.duration, max(cursor, silence.start + padding))
        end = min(info.duration, max(start, silence.end - padding))
        if end - start < 0.25:
            continue
        if start > cursor + 0.04:
            keeps.append(Cut(start=cursor, end=start,
                             rationale="Retained content before a detected silent interval", confidence=0.75))
        cursor = end
    if info.duration > cursor + 0.04:
        keeps.append(Cut(start=cursor, end=info.duration,
                         rationale="Retained source content", confidence=0.75))
    if not keeps:
        keeps = [Cut(start=0, end=info.duration,
                     rationale="No safe retained range; keep the whole source for review", confidence=0.25)]
    return EditPlan(source_path=info.path, source_duration=info.duration,
                    fps=info.fps, preset=preset, keeps=keeps)


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remaining = divmod(milliseconds, 3600000)
    minutes, remaining = divmod(remaining, 60000)
    secs, ms = divmod(remaining, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def to_srt(segments: list[Segment]) -> str:
    last = 0.0
    entries = []
    for i, segment in enumerate(segments, 1):
        if segment.start < last:
            raise ValueError("Transcript segments overlap or are unsorted")
        last = segment.end
        entries.append(f"{i}\n{srt_timestamp(segment.start)} --> {srt_timestamp(segment.end)}\n{segment.text.strip()}\n")
    return "\n".join(entries)


def retime_transcript(segments: list[Segment], plan: EditPlan) -> list[Segment]:
    result, offset = [], 0.0
    for cut in plan.keeps:
        for segment in segments:
            start, end = max(cut.start, segment.start), min(cut.end, segment.end)
            if end > start:
                result.append(Segment(start=offset + start - cut.start,
                                      end=offset + end - cut.start, text=segment.text))
        offset += cut.end - cut.start
    return result


def to_edl(plan: EditPlan) -> str:
    # CMX3600 non-drop-frame interchange is intentionally limited to integer rates.
    fps = round(plan.fps)
    if fps not in (24, 25, 30, 50, 60) or not math.isclose(plan.fps, fps, abs_tol=0.001):
        raise ValueError("EDL supports integer frame rates only; save JSON for fractional-rate media")
    def tc(frame):
        s, f = divmod(frame, fps)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h >= 24:
            raise ValueError("CMX3600 timecode must be less than 24 hours")
        return f"{h:02}:{m:02}:{s:02}:{f:02}"
    lines = ["TITLE: MADDY REVIEWED CUTS", "FCM: NON-DROP FRAME", ""]
    cursor = 0
    for i, cut in enumerate(plan.keeps, 1):
        start, end = round(cut.start * fps), round(cut.end * fps)
        if end <= start:
            raise ValueError("A retained range is shorter than one frame")
        length = end - start
        lines += [f"{i:03}  AX       AA/V  C        {tc(start)} {tc(end)} {tc(cursor)} {tc(cursor + length)}",
                  f"* FROM CLIP NAME: {plan.source_path.replace(chr(10), '').replace(chr(13), '')}", ""]
        cursor += length
    return "\n".join(lines)
