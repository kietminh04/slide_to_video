"""Engine nối toàn bộ pipeline: extract → plan → generate → guard → style → timeline."""

from __future__ import annotations

import json
from pathlib import Path

from codebase.clsg.config import Settings, get_settings
from codebase.clsg.extract import extract
from codebase.clsg.generate import generate as generate_scenes
from codebase.clsg.llm import FakeLLMProvider, LLMProvider, OpenAIProvider
from codebase.clsg.plan import plan
from codebase.clsg.schemas import (
    Chunk,
    Script,
    ScriptMeta,
    WeightProfile,
)
from codebase.clsg.style import apply_style


def _compute_timeline(script: Script) -> Script:
    """Tính est_s từ số âm tiết, cộng dồn t_start/t_end.

    Ước lượng đơn giản: số từ / (wpm/60).
    """
    wpm = 140  # TODO: lấy từ settings
    wps = wpm / 60.0
    t = 0.0

    for scene in script.scenes:
        scene.t_start = t
        scene_duration = 0.0
        for beat in scene.beats:
            word_count = len(beat.display_text.split())
            beat_duration = word_count / wps
            beat.est_s = round(beat_duration, 2)
            scene_duration += beat_duration
        scene.t_end = round(t + scene_duration, 2)
        t = scene.t_end

    return script


def run_pipeline(
    doc_path: Path,
    weights_path: Path,
    *,
    fake: bool = False,
    style_pack: str = "serious",
    settings: Settings | None = None,
) -> Script:
    """Chạy toàn bộ pipeline từ tài liệu và trọng số.

    Args:
        doc_path: Đường dẫn tài liệu (PPTX, DOCX, PDF, TXT).
        weights_path: Đường dẫn file trọng số JSON.
        fake: Nếu True, dùng FakeLLMProvider (cho test).
        style_pack: Tên style pack.
        settings: Cấu hình (mặc định đọc từ env).

    Returns:
        Script hoàn chỉnh.
    """
    settings = settings or get_settings()

    # === Khởi tạo LLM provider ===
    if fake:
        llm: LLMProvider = FakeLLMProvider()
        llm_judge: LLMProvider = FakeLLMProvider()
    else:
        llm = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            cache_dir=settings.llm_cache_dir,
            usage_log=settings.usage_log_file,
            default_model=settings.model_generator,
        )
        llm_judge = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            cache_dir=settings.llm_cache_dir,
            usage_log=settings.usage_log_file,
            default_model=settings.model_judge,
        )

    # === Đọc trọng số ===
    weights_data = json.loads(weights_path.read_text(encoding="utf-8"))
    weights = WeightProfile(**weights_data)

    # === Pipeline ===
    # 1. Extract
    chunks: list[Chunk] = extract(doc_path)

    # 2. Plan
    blueprint = plan(chunks, weights, settings, llm)

    # 3. Generate
    scenes, fact_sheets = generate_scenes(blueprint, chunks, llm, settings)

    # 4. Tạo Script
    weight_dict = {seg.chapter: seg.weight for seg in blueprint.segments}
    script = Script(
        meta=ScriptMeta(
            doc_id=doc_path.stem,
            duration_s=int(settings.minutes * 60),
            style=style_pack,
            weights=weight_dict,
        ),
        scenes=scenes,
    )

    # 5. Guard
    from codebase.clsg.guard import Guard
    guard_instance = Guard(llm=llm_judge, settings=settings)
    _report = guard_instance.check_script(script, blueprint, chunks, fact_sheets)
    # TODO: vòng sửa nếu report.passed == False

    # 6. Style
    script = apply_style(script, style_pack, llm, settings)

    # 7. Timeline
    script = _compute_timeline(script)

    return script
