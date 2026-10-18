import math
import pytest
from pydantic import ValidationError
from services.agent.models import (Preset, Span, Cut, EditPlan, Segment, create_plan,
                                   to_srt, to_edl, retime_transcript)


def test_silence_padding_preserves_context(media_info):
    plan = create_plan(media_info, [Span(start=2, end=4)], Preset.CAR)
    assert [(c.start, c.end) for c in plan.keeps] == [(0, 2.25), (3.75, 10)]
    assert plan.output_duration == 8.5


def test_overlapping_silences_are_merged_safely(media_info):
    plan = create_plan(media_info, [Span(start=2, end=6), Span(start=4, end=8)], Preset.CAR)
    assert all(a.end <= b.start for a, b in zip(plan.keeps, plan.keeps[1:]))


@pytest.mark.parametrize("start,end", [(1, 1), (5, 2), (-1, 3), (0, float("inf")), (float("nan"), 4)])
def test_reject_invalid_ranges(start, end):
    with pytest.raises(ValidationError):
        Span(start=start, end=end)


def test_plan_rejects_overlaps_and_beyond_source(media_info):
    data = create_plan(media_info, [], Preset.CAR).model_dump()
    for ranges in ([Cut(start=0, end=6, rationale="test", confidence=1),
                    Cut(start=5, end=9, rationale="test", confidence=1)],
                   [Cut(start=0, end=11, rationale="test", confidence=1)]):
        with pytest.raises(ValidationError):
            EditPlan.model_validate({**data, "keeps": ranges})


def test_unicode_srt_and_retiming(media_info):
    plan = create_plan(media_info, [Span(start=2, end=4)], Preset.CAR)
    segments = [Segment(start=4, end=5, text="ಕನ್ನಡ English")]
    retimed = retime_transcript(segments, plan)
    assert retimed[0].start == 2.5
    assert "00:00:02,500 --> 00:00:03,500" in to_srt(retimed)
    assert "ಕನ್ನಡ" in to_srt(retimed)


def test_srt_rejects_overlapping_cues():
    with pytest.raises(ValueError):
        to_srt([Segment(start=0, end=2, text="a"), Segment(start=1, end=3, text="b")])


def test_edl_records_are_contiguous_and_fractional_fps_is_gated(media_info):
    plan = create_plan(media_info, [Span(start=2, end=4)], Preset.CAR)
    edl = to_edl(plan)
    assert "FCM: NON-DROP FRAME" in edl
    assert "00:00:02:06" in edl
    assert "00:00:08:12" in edl or "00:00:08:13" in edl
    with pytest.raises(ValueError, match="integer frame rates"):
        to_edl(plan.model_copy(update={"fps": 29.97}))


def test_hash_changes_with_content(media_info):
    plan = create_plan(media_info, [], Preset.CAR)
    other = plan.model_copy(update={"preset": Preset.TRAVEL})
    assert plan.digest() != other.digest()
