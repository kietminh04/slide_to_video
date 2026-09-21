"""Schema dữ liệu cho CLSG pipeline.

File này là hợp đồng giữa các module. Giữ tên trường ổn định
vì fixture, UI và eval đều phụ thuộc vào chúng.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# === Kiểu dùng chung ===

Depth = Literal["bridge", "core", "deep"]
BeatType = Literal["claim", "bridge", "example", "flavor", "question"]
Verdict = Literal["supported", "contradicted", "not_found"]


# === Extract ===

class Chunk(BaseModel):
    """Một đoạn văn bản trích từ tài liệu nguồn."""
    id: str = Field(description='VD: "c_0412", ổn định giữa các lần chạy')
    chapter: str = Field(description='VD: "ch2"')
    text: str
    page: int | None = None
    kind: Literal["text", "table", "caption"] = "text"
    needs_human: bool = Field(
        default=False, description="Slide chỉ có hình, trang trích quá ít text"
    )


# === Plan ===

class WeightProfile(BaseModel):
    """Vector trọng số theo chương từ nhiều nguồn."""
    chapters: list[str]
    w_teacher: list[float] | None = None
    w_quiz: list[float] | None = None  # 1 - tỉ lệ đúng; KHÔNG chứa điểm thô
    w_user: list[float] | None = None
    prereq: list[bool] | None = None
    alpha: float = 0.4
    beta: float = 0.4
    gamma: float = 0.2


class TeachingPoint(BaseModel):
    """Một điểm dạy được chọn cho một đoạn."""
    title: str
    chunk_ids: list[str]
    misconception: str | None = None  # lấy từ câu quiz sai nếu có


class Segment(BaseModel):
    """Một đoạn trong kế hoạch, tương ứng một chương."""
    chapter: str
    weight: float
    word_budget: int
    depth: Depth
    points: list[TeachingPoint] = []


class Blueprint(BaseModel):
    """Kế hoạch tổng thể cho toàn bài giảng."""
    minutes: float
    wpm: int
    segments: list[Segment]


# === Generate ===

class Fact(BaseModel):
    """Một dữ kiện trích từ chunk nguồn."""
    kind: Literal["number", "example", "cause", "exception", "definition"]
    text: str
    chunk_id: str


class FactSheet(BaseModel):
    """Phiếu dữ kiện trích từ nguyên văn chunk."""
    segment_chapter: str
    facts: list[Fact]


class Prosody(BaseModel):
    """Thông tin ngữ điệu và nhịp độ sư phạm (Prosody & Pause Planner)."""
    emotion: str | None = None
    rate: float = 1.0
    pause_after_ms: int = 0
    pause_type: str | None = None  # VD: "dramatic_pause", "visual_sync_pause", "cognitive_pause", "structural_pause"
    pedagogical_intent: str | None = None  # Mục đích sư phạm của khoảng dừng này
    emphasis: list[str] = []


class Beat(BaseModel):
    """Một nhịp trong kịch bản – đơn vị nhỏ nhất."""
    speaker: str = "F1"
    type: BeatType
    display_text: str
    tts_text: str | None = None  # để cửa cho đội video về sau
    source_ids: list[str] = []
    fact_ids: list[int] = []  # chỉ số trong FactSheet đã dùng
    prosody: Prosody = Field(default_factory=Prosody)
    est_s: float | None = None
    actual_s: float | None = None


class Visual(BaseModel):
    """Gợi ý hình ảnh cho đoạn (Visual Intent Generator)."""
    layout: str = "title+bullets"
    on_screen_text: list[str] = []
    asset_hint: str | None = None  # "slide 14, hình 2" hoặc mô tả chi tiết hình ảnh cần render (ví dụ: process_visualization, equation)
    visual_type: str | None = None  # VD: "process_visualization", "equation", "diagram"
    visual_purpose: str | None = None # VD: "Trực quan hóa hoạt cảnh chuyển động..."


class Scene(BaseModel):
    """Một cảnh – tương ứng một đoạn trong kịch bản."""
    id: str
    chapter: str
    depth: Depth
    t_start: float = 0.0
    t_end: float = 0.0
    visual: Visual = Field(default_factory=Visual)
    beats: list[Beat]
    needs_human: bool = False


class ScriptMeta(BaseModel):
    """Metadata của toàn bộ kịch bản."""
    doc_id: str
    duration_s: int
    style: str
    weights: dict[str, float]
    models: dict[str, str] = {}  # vai trò -> tên model đã dùng


class Script(BaseModel):
    """Kịch bản hoàn chỉnh."""
    meta: ScriptMeta
    scenes: list[Scene]


# === Guard ===

class ClaimCheck(BaseModel):
    """Kết quả kiểm tra một claim."""
    scene_id: str
    beat_index: int
    verdict: Verdict
    note: str | None = None


class GuardReport(BaseModel):
    """Báo cáo kiểm tra chất lượng kịch bản."""
    pacing_dev: dict[str, float]  # theo scene
    allocation_l1: float
    missing_sources: list[str]
    depth_ok: dict[str, bool]
    claim_checks: list[ClaimCheck]
    passed: bool
    rounds: int = 0


# === Validation ===

def validate_script(script: Script, chunks: list[Chunk]) -> list[str]:
    """Kiểm tra các bất biến của kịch bản.

    Trả về danh sách lỗi (rỗng nếu hợp lệ).
    """
    errors: list[str] = []
    chunk_ids = {c.id for c in chunks}

    # 1. Mọi Beat.type == "claim" phải có ít nhất một source_ids,
    #    và mọi id đó phải tồn tại trong danh sách Chunk.
    for scene in script.scenes:
        for i, beat in enumerate(scene.beats):
            if beat.type == "claim":
                if not beat.source_ids:
                    errors.append(
                        f"Scene {scene.id}, beat {i}: claim không có source_ids"
                    )
                for sid in beat.source_ids:
                    if sid not in chunk_ids:
                        errors.append(
                            f"Scene {scene.id}, beat {i}: source_id '{sid}' không tồn tại"
                        )

    # 2. Tổng weight xấp xỉ 1 (chỉ kiểm tra nếu có scene – trong Script
    #    không có Segment, nên bỏ qua kiểm tra này ở đây)

    # 3. t_end >= t_start, các scene không chồng thời gian
    prev_end = 0.0
    for scene in script.scenes:
        if scene.t_end < scene.t_start:
            errors.append(
                f"Scene {scene.id}: t_end ({scene.t_end}) < t_start ({scene.t_start})"
            )
        if scene.t_start < prev_end:
            errors.append(
                f"Scene {scene.id}: chồng thời gian (t_start={scene.t_start} < prev_end={prev_end})"
            )
        prev_end = scene.t_end

    # 4. Beat flavor chiếm không quá 20% tổng số từ
    total_words = 0
    flavor_words = 0
    for scene in script.scenes:
        for beat in scene.beats:
            words = len(beat.display_text.split())
            total_words += words
            if beat.type == "flavor":
                flavor_words += words
    if total_words > 0 and flavor_words / total_words > 0.20:
        errors.append(
            f"Beat flavor chiếm {flavor_words / total_words:.0%} tổng số từ (tối đa 20%)"
        )

    return errors
