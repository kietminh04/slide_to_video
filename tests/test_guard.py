import pytest

from codebase.clsg.config import get_settings
from codebase.clsg.guard import Guard, JudgeResult
from codebase.clsg.llm import FakeLLMProvider
from codebase.clsg.schemas import (
    Beat,
    Blueprint,
    Chunk,
    ClaimCheck,
    Fact,
    FactSheet,
    Scene,
    Script,
    ScriptMeta,
    Segment,
)


class MockLLMProvider(FakeLLMProvider):
    def __init__(self, checks: list[ClaimCheck]):
        super().__init__()
        self.checks = checks

    def generate(self, prompt, response_model, model="", step=""):
        if response_model == JudgeResult:
            return JudgeResult(checks=self.checks)
        return super().generate(prompt, response_model, model, step)


@pytest.fixture
def base_data():
    settings = get_settings(
        pacing_threshold=0.15,
        allocation_l1_threshold=0.15,
        min_facts_deep=1,
    )
    chunks = [
        Chunk(id="c1", chapter="ch1", text="text c1"),
        Chunk(id="c2", chapter="ch2", text="text c2")
    ]
    blueprint = Blueprint(
        minutes=5.0,
        wpm=100,
        segments=[
            Segment(chapter="ch1", weight=0.5, word_budget=50, depth="bridge"),
            Segment(chapter="ch2", weight=0.5, word_budget=50, depth="deep")
        ]
    )
    text_50 = " ".join(["word"] * 50)

    script = Script(
        meta=ScriptMeta(doc_id="d1", duration_s=300, style="style", weights={"ch1": 0.5, "ch2": 0.5}),
        scenes=[
            Scene(
                id="s1",
                chapter="ch1",
                depth="bridge",
                beats=[Beat(type="claim", display_text=text_50, source_ids=["c1"])]
            ),
            Scene(
                id="s2",
                chapter="ch2",
                depth="deep",
                beats=[Beat(type="claim", display_text=text_50, source_ids=["c2"], fact_ids=[0])]
            )
        ]
    )
    fact_sheets = {
        "ch2": FactSheet(
            segment_chapter="ch2",
            facts=[Fact(kind="number", text="fact 1", chunk_id="c2")]
        )
    }
    llm = MockLLMProvider(checks=[
        ClaimCheck(scene_id="s1", beat_index=0, verdict="supported"),
        ClaimCheck(scene_id="s2", beat_index=0, verdict="supported")
    ])

    return script, blueprint, chunks, fact_sheets, llm, settings


def test_guard_pass(base_data):
    script, blueprint, chunks, fact_sheets, llm, settings = base_data
    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)
    assert report.passed is True


def test_guard_missing_source(base_data):
    script, blueprint, chunks, fact_sheets, llm, settings = base_data
    script.scenes[0].beats[0].source_ids.append("c3")

    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)

    assert report.passed is False
    assert "c3" in report.missing_sources


def test_guard_pacing_dev(base_data):
    script, blueprint, chunks, fact_sheets, llm, settings = base_data
    text_100 = " ".join(["word"] * 100)
    script.scenes[0].beats[0].display_text = text_100

    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)

    assert report.passed is False
    assert report.pacing_dev["s1"] == 1.0


def test_guard_allocation_l1(base_data):
    script, blueprint, chunks, fact_sheets, llm, settings = base_data
    script.scenes[0].beats[0].display_text = " ".join(["w"] * 100)
    script.scenes[1].beats[0].display_text = ""

    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)

    assert report.passed is False
    assert report.allocation_l1 == 1.0


def test_guard_depth_fail(base_data):
    script, blueprint, chunks, fact_sheets, llm, settings = base_data
    fact_sheets["ch2"].facts[0].kind = "definition"

    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)

    assert report.passed is False
    assert report.depth_ok["s2"] is False


def test_guard_claim_contradicted(base_data):
    script, blueprint, chunks, fact_sheets, _, settings = base_data
    llm = MockLLMProvider(checks=[
        ClaimCheck(scene_id="s1", beat_index=0, verdict="contradicted")
    ])

    guard = Guard(llm=llm, settings=settings)
    report = guard.check_script(script, blueprint, chunks, fact_sheets)

    assert report.passed is False
