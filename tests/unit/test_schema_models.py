from datetime import datetime

import pytest

from grimoire.core.schema import (
    DangerScores,
    DangerType,
    SourceRef,
    SourceType,
    Step,
    Trace,
    TraceBundle,
)


def test_danger_scores_clips_and_populates() -> None:
    scores = DangerScores(scores={DangerType.AMBIGUITY: 2.5})
    assert scores.score(DangerType.AMBIGUITY) == 1.0
    assert scores.score(DangerType.ADVERSARIAL) == 0.0


def test_step_requires_non_empty_text() -> None:
    with pytest.raises(ValueError, match="step.text must be non-empty"):
        Step(
            step_id="s1",
            trace_id="t1",
            index=0,
            text="  ",
        )


def test_trace_bundle_trace_id_consistency() -> None:
    trace = Trace(trace_id="t1")
    step = Step(step_id="s1", trace_id="t2", index=0, text="ok")
    with pytest.raises(ValueError, match="trace_id mismatch"):
        TraceBundle(trace=trace, steps=[step])


def test_trace_bundle_happy_path() -> None:
    trace = Trace(trace_id="t1", created_at=datetime.utcnow())
    step = Step(step_id="s1", trace_id="t1", index=0, text="ok")
    bundle = TraceBundle(trace=trace, steps=[step])
    assert bundle.trace.trace_id == "t1"


def test_source_ref_accepts_source_type() -> None:
    source = SourceRef(source_type=SourceType.HUGGINGFACE)
    assert source.source_type == SourceType.HUGGINGFACE
