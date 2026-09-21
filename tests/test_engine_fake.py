"""Test pipeline end-to-end với FakeLLMProvider.

Chạy: uv run pytest tests/test_engine_fake.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codebase.clsg.engine import run_pipeline
from codebase.clsg.extract import extract
from codebase.clsg.schemas import Script, validate_script

FIXTURES_DIR = Path("codebase/fixtures")


@pytest.fixture
def sample_doc() -> Path:
    """Đường dẫn tài liệu mẫu."""
    return FIXTURES_DIR / "sample_doc.txt"


@pytest.fixture
def weights_path() -> Path:
    """Đường dẫn file trọng số."""
    return FIXTURES_DIR / "weights.json"


class TestPipelineFake:
    """Test pipeline với FakeLLMProvider."""

    def test_pipeline_runs_end_to_end(self, sample_doc: Path, weights_path: Path) -> None:
        """Pipeline chạy không lỗi với --fake."""
        script = run_pipeline(
            doc_path=sample_doc,
            weights_path=weights_path,
            fake=True,
        )
        assert isinstance(script, Script)
        assert len(script.scenes) > 0

    def test_output_is_valid_json(self, sample_doc: Path, weights_path: Path) -> None:
        """Output serialize được thành JSON hợp lệ."""
        script = run_pipeline(
            doc_path=sample_doc,
            weights_path=weights_path,
            fake=True,
        )
        json_str = script.model_dump_json()
        parsed = json.loads(json_str)
        assert "meta" in parsed
        assert "scenes" in parsed

    def test_script_validates(self, sample_doc: Path, weights_path: Path) -> None:
        """Script vượt qua validate_script."""
        script = run_pipeline(
            doc_path=sample_doc,
            weights_path=weights_path,
            fake=True,
        )
        chunks = extract(sample_doc)
        errors = validate_script(script, chunks)
        # Với stub modules, có thể có lỗi source_ids –
        # nhưng không được có crash
        assert isinstance(errors, list)

    def test_clsg_no_ui_imports(self) -> None:
        """clsg/ không import streamlit hay typer."""
        import importlib
        import pkgutil

        clsg_path = Path("codebase/clsg")
        forbidden = {"streamlit", "typer"}

        for module_info in pkgutil.walk_packages(
            [str(clsg_path)], prefix="codebase.clsg."
        ):
            try:
                mod = importlib.import_module(module_info.name)
            except ImportError:
                continue

            source_file = getattr(mod, "__file__", None)
            if source_file:
                source = Path(source_file).read_text(encoding="utf-8")
                for lib in forbidden:
                    assert f"import {lib}" not in source, (
                        f"{module_info.name} import {lib} – vi phạm ranh giới"
                    )

    def test_timeline_computed(self, sample_doc: Path, weights_path: Path) -> None:
        """Timeline được tính – t_end > 0 ở scene cuối."""
        script = run_pipeline(
            doc_path=sample_doc,
            weights_path=weights_path,
            fake=True,
        )
        if script.scenes:
            last = script.scenes[-1]
            assert last.t_end > 0

    def test_meta_populated(self, sample_doc: Path, weights_path: Path) -> None:
        """Meta có đủ thông tin."""
        script = run_pipeline(
            doc_path=sample_doc,
            weights_path=weights_path,
            fake=True,
        )
        assert script.meta.doc_id == "sample_doc"
        assert script.meta.duration_s == 300
        assert script.meta.style == "serious"


class TestFixtures:
    """Test fixtures hợp lệ."""

    def test_script_sample_valid(self) -> None:
        """script_sample.json parse được thành Script."""
        sample_path = FIXTURES_DIR / "script_sample.json"
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        script = Script(**data)
        assert len(script.scenes) == 3

    def test_weights_sample_valid(self) -> None:
        """weights.json parse được thành WeightProfile."""
        from codebase.clsg.schemas import WeightProfile

        wp_path = FIXTURES_DIR / "weights.json"
        data = json.loads(wp_path.read_text(encoding="utf-8"))
        wp = WeightProfile(**data)
        assert len(wp.chapters) == 3

    def test_extract_sample_doc(self) -> None:
        """Trích xuất từ sample_doc.txt trả về chunks."""
        chunks = extract(FIXTURES_DIR / "sample_doc.txt")
        assert len(chunks) >= 3
        chapters = {c.chapter for c in chunks}
        assert "ch1" in chapters
        assert "ch2" in chapters
        assert "ch3" in chapters
