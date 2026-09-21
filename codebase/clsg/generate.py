"""Sinh kịch bản từ Blueprint – hai bước cho đoạn deep.

Module này thực hiện sinh kịch bản (Scene) từ Blueprint.
- Tính dàn ý (outline), tóm tắt đoạn trước, ngân sách từ.
- Đoạn deep: trích FactSheet → viết beat.
- Đoạn core/bridge: viết beat theo khuôn.
- Tự động kiểm tra `source_ids` cho claim beat.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codebase.clsg.config import Settings
from codebase.clsg.llm import LLMProvider
from codebase.clsg.schemas import Blueprint, Chunk, FactSheet, Scene


def generate(
    blueprint: Blueprint,
    chunks: list[Chunk],
    llm: LLMProvider,
    settings: Settings,
) -> tuple[list[Scene], dict[str, FactSheet]]:
    """Sinh danh sách Scene từ Blueprint.

    Mỗi đoạn sinh riêng lẻ, nhận dàn ý toàn bài, tóm tắt đoạn trước,
    chunk của đoạn, ngân sách từ và mức sâu.

    Đoạn deep: trích FactSheet → viết beat.
    Đoạn core: viết beat theo khuôn.
    Đoạn bridge: một câu nối (thực hiện tương tự core).

    Args:
        blueprint: Kế hoạch bài giảng.
        chunks: Danh sách chunk nguồn.
        llm: LLM provider.
        settings: Cấu hình pipeline.

    Returns:
        tuple gồm (Danh sách Scene, dict các FactSheet với key là chapter).
    """
    scenes: list[Scene] = []
    fact_sheets: dict[str, FactSheet] = {}
    chunk_by_chapter: dict[str, list[Chunk]] = {}
    for c in chunks:
        chunk_by_chapter.setdefault(c.chapter, []).append(c)

    # Cấu hình Jinja2 để render prompt
    prompts_dir = Path(__file__).parent / "prompts"
    env = Environment(loader=FileSystemLoader(prompts_dir))
    factsheet_tmpl = env.get_template("factsheet.j2")
    write_tmpl = env.get_template("write.j2")

    outline = [(seg.chapter, seg.word_budget) for seg in blueprint.segments]
    previous_summary = ""

    for i, seg in enumerate(blueprint.segments):
        chapter_chunks = chunk_by_chapter.get(seg.chapter, [])
        if not chapter_chunks:
            # Nếu không có chunk, tạo fallback cảnh rỗng
            scenes.append(
                Scene(
                    id=f"s_{seg.chapter}",
                    chapter=seg.chapter,
                    depth=seg.depth,
                    beats=[]
                )
            )
            continue

        factsheet = None
        if seg.depth == "deep":
            # 1. Trích FactSheet
            prompt_fact = factsheet_tmpl.render(
                segment=seg,
                chunks=chapter_chunks,
                settings=settings,
            )
            factsheet = llm.generate(
                prompt=prompt_fact,
                response_model=FactSheet,
                model=settings.model_generator,
                step="extract_factsheet",
            )

        # 2. Viết beat
        prompt_write = write_tmpl.render(
            segment=seg,
            outline=outline,
            previous_summary=previous_summary,
            factsheet=factsheet,
            chunks=chapter_chunks,
            enumerate=enumerate,
        )

        scene = llm.generate(
            prompt=prompt_write,
            response_model=Scene,
            model=settings.model_generator,
            step=f"write_scene_{seg.depth}",
        )

        # Ép kiểu các trường định danh cơ bản
        scene.id = f"s_{seg.chapter}"
        scene.chapter = seg.chapter
        scene.depth = seg.depth

        # Kiểm tra và fallback source_ids cho claim
        default_source_id = chapter_chunks[0].id
        for beat in scene.beats:
            if beat.type == "claim":
                if not beat.source_ids:
                    beat.source_ids = [default_source_id]

        scenes.append(scene)

        # Cập nhật previous_summary cho đoạn sau
        summary_texts = [b.display_text for b in scene.beats if b.type == "claim"]
        if summary_texts:
            previous_summary = f"Chương trước ({seg.chapter}) đã nói về: " + " ".join(summary_texts[:2])
        else:
            previous_summary = f"Chương trước ({seg.chapter}) đã hoàn tất."

        if factsheet:
            fact_sheets[seg.chapter] = factsheet

    return scenes, fact_sheets
