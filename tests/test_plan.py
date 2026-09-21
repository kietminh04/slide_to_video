import pytest

from codebase.clsg.config import Settings
from codebase.clsg.llm import FakeLLMProvider
from codebase.clsg.plan import plan
from codebase.clsg.schemas import Chunk, WeightProfile


def test_plan_valid():
    weights = WeightProfile(
        chapters=["ch1", "ch2"],
        w_teacher=[0.5, 0.5],
        alpha=1.0,
    )
    chunks = [
        Chunk(id="c1", chapter="ch1", text="text 1"),
        Chunk(id="c2", chapter="ch2", text="text 2"),
    ]
    settings = Settings(minutes=5.0, wpm=150)
    llm = FakeLLMProvider()

    blueprint = plan(chunks, weights, settings, llm)
    assert len(blueprint.segments) == 2
    assert blueprint.segments[0].weight == 0.5
    assert blueprint.segments[1].weight == 0.5
    assert sum(s.word_budget for s in blueprint.segments) == 750

def test_plan_empty_weights_raises():
    weights = WeightProfile(chapters=["ch1"])
    # All weights are None
    settings = Settings()
    llm = FakeLLMProvider()

    with pytest.raises(ValueError, match="Tất cả trọng số đều trống"):
        plan([], weights, settings, llm)
