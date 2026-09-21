from pathlib import Path

from codebase.clsg.eval.run_eval import run_eval
from codebase.clsg.schemas import Beat, Scene, Script, ScriptMeta


class FakeLLMProvider:
    def __init__(self, **kwargs):
        pass

    def generate_structured(self, prompt: str, schema: type) -> Script:
        # Mock trả về Script hợp lệ
        return Script(
            meta=ScriptMeta(
                doc_id="test",
                duration_s=300,
                style="academic",
                weights={"ch1": 0.5, "ch2": 0.5}
            ),
            scenes=[
                Scene(
                    id="s1",
                    chapter="ch1",
                    depth="core",
                    beats=[
                        Beat(type="claim", display_text="Đây là ch1.", source_ids=["c1"])
                    ]
                )
            ]
        )

    def __call__(self, prompt: str, schema: type = None) -> Script:
        return self.generate_structured(prompt, schema)

# Cần mock run_pipeline để chạy cho các test nếu codebase.clsg.engine chưa hoàn thiện
# Nhưng vì yêu cầu là gọi engine.run_pipeline và đọc Script, có thể FakeLLMProvider
# sẽ làm cho engine.run_pipeline trả về Script thành công.
# Để an toàn cho CI, ta có thể dùng monkeypatch cho run_pipeline trong test

def dummy_run_pipeline(doc_id, chunks, weights, llm_provider, **kwargs):
    return llm_provider.generate_structured("dummy", Script)

def test_run_eval(monkeypatch):
    # Mock engine.run_pipeline để dùng FakeLLMProvider đơn giản trả về Script
    from codebase.clsg import engine
    monkeypatch.setattr(engine, "run_pipeline", dummy_run_pipeline)

    # Tạo 2 cases giả
    data_dir = Path(__file__).parent.parent / "codebase" / "clsg" / "eval" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    import json

    dummy_case_1 = {
        "doc_id": "test1",
        "chunks": [
            {"id": "c1", "chapter": "ch1", "text": "Test 1 text c1", "needs_human": False, "kind": "text"},
            {"id": "c2", "chapter": "ch2", "text": "Test 1 text c2", "needs_human": False, "kind": "text"}
        ],
        "weights_focus": {"ch1": 0.8, "ch2": 0.2},
        "weights_even": {"ch1": 0.5, "ch2": 0.5}
    }

    dummy_case_2 = {
        "doc_id": "test2",
        "chunks": [
            {"id": "c3", "chapter": "ch3", "text": "Test 2 text c3", "needs_human": False, "kind": "text"}
        ],
        "weights_focus": {"ch3": 1.0},
        "weights_even": {"ch3": 1.0}
    }

    with open(data_dir / "case1.json", "w", encoding="utf-8") as f:
        json.dump(dummy_case_1, f)
    with open(data_dir / "case2.json", "w", encoding="utf-8") as f:
        json.dump(dummy_case_2, f)

    provider = FakeLLMProvider()
    results = run_eval(provider)

    assert "case1" in results
    assert "case2" in results
    assert "baseline" in results["case1"]
    assert "pipeline" in results["case1"]
    assert "ablation" in results["case1"]

    # Dọn dẹp file test
    (data_dir / "case1.json").unlink(missing_ok=True)
    (data_dir / "case2.json").unlink(missing_ok=True)
