# Schema tham chiếu (`clsg/schemas.py`)

Đọc file này khi tạo hoặc sửa `schemas.py`. Đây là hợp đồng giữa các module; giữ tên trường ổn định vì fixture, UI và eval đều phụ thuộc vào chúng.

```python
from typing import Literal
from pydantic import BaseModel, Field

Depth = Literal["bridge", "core", "deep"]
BeatType = Literal["claim", "bridge", "example", "flavor", "question"]
Verdict = Literal["supported", "contradicted", "not_found"]

class Chunk(BaseModel):
    id: str                      # "c_0412", ổn định giữa các lần chạy
    chapter: str                 # "ch2"
    text: str
    page: int | None = None
    kind: Literal["text", "table", "caption"] = "text"
    needs_human: bool = False    # slide chỉ có hình, trang trích được quá ít text

class WeightProfile(BaseModel):
    chapters: list[str]
    w_teacher: list[float] | None = None
    w_quiz: list[float] | None = None      # 1 - tỉ lệ đúng; KHÔNG chứa điểm thô
    w_user: list[float] | None = None
    prereq: list[bool] | None = None
    alpha: float = 0.4; beta: float = 0.4; gamma: float = 0.2

class TeachingPoint(BaseModel):
    title: str
    chunk_ids: list[str]
    misconception: str | None = None       # lấy từ câu quiz sai nếu có

class Segment(BaseModel):
    chapter: str
    weight: float
    word_budget: int
    depth: Depth
    points: list[TeachingPoint] = []

class Blueprint(BaseModel):
    minutes: float
    wpm: int
    segments: list[Segment]

class Fact(BaseModel):
    kind: Literal["number", "example", "cause", "exception", "definition"]
    text: str
    chunk_id: str

class FactSheet(BaseModel):
    segment_chapter: str
    facts: list[Fact]

class Prosody(BaseModel):                  # để trống trong bản 3 ngày
    emotion: str | None = None
    rate: float = 1.0
    pause_after_ms: int = 0
    emphasis: list[str] = []

class Beat(BaseModel):
    speaker: str = "F1"
    type: BeatType
    display_text: str
    tts_text: str | None = None            # để cửa cho đội video về sau
    source_ids: list[str] = []
    fact_ids: list[int] = []               # chỉ số trong FactSheet đã dùng
    prosody: Prosody = Prosody()
    est_s: float | None = None
    actual_s: float | None = None

class Visual(BaseModel):
    layout: str = "title+bullets"
    on_screen_text: list[str] = []
    asset_hint: str | None = None          # "slide 14, hình 2"

class Scene(BaseModel):
    id: str
    chapter: str
    depth: Depth
    t_start: float = 0.0
    t_end: float = 0.0
    visual: Visual = Visual()
    beats: list[Beat]
    needs_human: bool = False

class ScriptMeta(BaseModel):
    doc_id: str
    duration_s: int
    style: str
    weights: dict[str, float]
    models: dict[str, str] = {}            # vai trò -> tên model đã dùng

class Script(BaseModel):
    meta: ScriptMeta
    scenes: list[Scene]

class ClaimCheck(BaseModel):
    scene_id: str
    beat_index: int
    verdict: Verdict
    note: str | None = None

class GuardReport(BaseModel):
    pacing_dev: dict[str, float]           # theo scene
    allocation_l1: float
    missing_sources: list[str]
    depth_ok: dict[str, bool]
    claim_checks: list[ClaimCheck]
    passed: bool
    rounds: int = 0
```

## Bất biến cần validate

- Mọi `Beat.type == "claim"` có ít nhất một `source_ids`, và mọi id đó tồn tại trong danh sách `Chunk`.
- Tổng `Segment.weight` xấp xỉ 1.
- `t_end >= t_start`, các scene không chồng thời gian.
- Beat `flavor` chiếm không quá 20% tổng số từ.

Viết các bất biến này thành `model_validator` hoặc hàm `validate_script(script, chunks)` và gọi trong guard, để lỗi lộ ra sớm thay vì lộ ra ở UI.
