import math

from pydantic import BaseModel

from codebase.clsg.config import Settings
from codebase.clsg.llm import LLMProvider
from codebase.clsg.schemas import Blueprint, Chunk, Segment, TeachingPoint, WeightProfile


class SelectResponse(BaseModel):
    points: list[TeachingPoint]


def plan(
    chunks: list[Chunk],
    weights: WeightProfile,
    settings: Settings,
    llm: LLMProvider,
) -> Blueprint:
    """Tạo kế hoạch phân bổ từ trọng số và chọn điểm dạy."""
    num_chapters = len(weights.chapters)
    final_w = [0.0] * num_chapters
    total_coef = 0.0

    # 1. Gộp trọng số
    if weights.w_teacher is not None and len(weights.w_teacher) == num_chapters:
        for i in range(num_chapters):
            final_w[i] += weights.w_teacher[i] * weights.alpha
        total_coef += weights.alpha

    if weights.w_quiz is not None and len(weights.w_quiz) == num_chapters:
        for i in range(num_chapters):
            final_w[i] += weights.w_quiz[i] * weights.beta
        total_coef += weights.beta

    if weights.w_user is not None and len(weights.w_user) == num_chapters:
        for i in range(num_chapters):
            final_w[i] += weights.w_user[i] * weights.gamma
        total_coef += weights.gamma

    if total_coef == 0:
        raise ValueError("Tất cả trọng số đều trống.")

    final_w = [w / total_coef for w in final_w]

    # 2. Focus
    # (Nếu settings không có w_focus thì ta giả định focus = 1.0 hoặc từ settings)
    focus = getattr(settings, "w_focus", 1.0)
    final_w = [math.pow(w, focus) for w in final_w]

    # 3. Áp sàn tiên quyết
    if weights.prereq and len(weights.prereq) == num_chapters:
        for i in range(num_chapters):
            if weights.prereq[i]:
                final_w[i] = max(final_w[i], settings.w_min)

    # 4. Chuẩn hóa lại
    total_w = sum(final_w)
    if total_w == 0:
        raise ValueError("Tổng trọng số bằng 0.")
    final_w = [w / total_w for w in final_w]

    # Phân bổ ngân sách
    total_words = int(settings.minutes * settings.wpm)
    segments = []
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "prompts")))

    for i, chapter in enumerate(weights.chapters):
        w = final_w[i]
        budget = int(w * total_words)

        # Determine depth based on budget proportion
        if w < 0.2:
            depth = "bridge"
        elif w > 0.4:
            depth = "deep"
        else:
            depth = "core"

        # Lấy chunks của chương này
        ch_chunks = [c for c in chunks if c.chapter == chapter]
        ch_text = "\n\n".join(c.text for c in ch_chunks)

        points = []
        if depth in ["core", "deep"]:
            try:
                template = env.get_template("select.j2")
                prompt = template.render(content=ch_text, budget=budget)
                resp = llm.generate(prompt, response_model=SelectResponse)
                points = resp.points
            except Exception:
                # Fallback
                title = ch_chunks[0].text[:50] + "..." if ch_chunks else "Nội dung"
                c_ids = [ch_chunks[0].id] if ch_chunks else []
                points = [TeachingPoint(title=title, chunk_ids=c_ids)]

        segments.append(
            Segment(
                chapter=chapter,
                weight=w,
                word_budget=budget,
                depth=depth,
                points=points
            )
        )

    return Blueprint(
        minutes=settings.minutes,
        wpm=settings.wpm,
        segments=segments,
    )
