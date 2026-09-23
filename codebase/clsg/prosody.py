"""Module ProsodyPlanner: Điều phối nhịp điệu sư phạm và ngắt nghỉ giọng đọc (PACLIC 2023 / CIKM 2025).

Cung cấp:
- Chèn nhịp ngắt nghỉ thông minh:
  + [P1] (Micro-pause 220ms): Ngắt nhịp ngữ pháp (dấu phẩy, liên từ tư duy).
  + [P2] (Sentence-pause 600ms): Ngắt câu kết thúc một luận điểm.
  + [P3] (Thinking-pause 1100ms): Khoảng lặng sau câu hỏi gợi mở hoặc lúc chuyển hình.
- Mô hình tính thời lượng hiệu chuẩn (Calibrated Duration Modeling):
  Duration = (Words / WPS) + Total_Pause_Seconds.
- Bộ biên dịch W3C SSML (<break time="..."/>) cho mọi engine TTS (Edge, Azure, ElevenLabs, Viettel, FPT).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PlannedBeat:
    """Đoạn văn bản sau khi được lập kế hoạch ngữ điệu và nhịp ngắt."""
    raw_text: str
    marked_text: str           # Văn bản chứa [P1], [P2], [P3]
    ssml_text: str             # Chuẩn W3C SSML với thẻ <break>
    clean_speech_text: str     # Văn bản trơn không chứa nhãn để đọc/làm phụ đề
    word_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    pause_total_s: float
    speech_duration_s: float
    calibrated_duration_s: float


class ProsodyPlanner:
    """Bộ điều phối nhịp độ và ngắt nghỉ sư phạm."""

    # Thời lượng mặc định từng loại ngắt nghỉ (giây)
    DEFAULT_P1_MS = 220
    DEFAULT_P2_MS = 600
    DEFAULT_P3_MS = 1100

    # Các từ nối tư duy tiếng Việt cần ngắt nhịp nhẹ [P1] sau từ
    DISCOURSE_CONNECTIVES = [
        r"\bTuy nhiên\b",
        r"\bDo đó\b",
        r"\bVì vậy\b",
        r"\bĐặc biệt là\b",
        r"\bCụ thể\b",
        r"\bCụ thể là\b",
        r"\bMặt khác\b",
        r"\bTrước hết\b",
        r"\bTiếp theo\b",
        r"\bNgược lại\b",
        r"\bTóm lại\b",
        r"\bNói cách khác\b",
        r"\bChẳng hạn như\b",
        r"\bVí dụ như\b",
    ]

    # Các mẫu câu hỏi tu từ / gợi mở cần khoảng lặng tư duy [P3]
    RHETORICAL_PATTERNS = [
        r"\bTại sao\b[^.!?]+[?]",
        r"\bLàm thế nào\b[^.!?]+[?]",
        r"\bÝ nghĩa của\b[^.!?]+[?]",
        r"\bLiệu rằng\b[^.!?]+[?]",
        r"\bVì sao lại\b[^.!?]+[?]",
        r"\bHãy tự hỏi\b[^.!?]+[?]",
    ]

    def __init__(
        self,
        wpm: int = 140,
        p1_ms: int = DEFAULT_P1_MS,
        p2_ms: int = DEFAULT_P2_MS,
        p3_ms: int = DEFAULT_P3_MS,
    ):
        self.wpm = wpm
        self.wps = wpm / 60.0
        self.p1_ms = p1_ms
        self.p2_ms = p2_ms
        self.p3_ms = p3_ms

    def plan(self, text: str, custom_wpm: int | None = None) -> PlannedBeat:
        """Phân tích văn bản và chèn các thẻ nhịp ngắt sư phạm [P1], [P2], [P3]."""
        if not text or not text.strip():
            return PlannedBeat(
                raw_text="", marked_text="", ssml_text="<speak></speak>",
                clean_speech_text="", word_count=0, p1_count=0, p2_count=0, p3_count=0,
                pause_total_s=0.0, speech_duration_s=0.0, calibrated_duration_s=0.0
            )

        wps = (custom_wpm / 60.0) if custom_wpm else self.wps
        marked = text.strip()

        # 1. BƯỚC 1: Đánh dấu [P3] cho các câu hỏi tu từ / gợi mở
        for pat in self.RHETORICAL_PATTERNS:
            marked = re.sub(
                f"({pat})",
                r"\1 [P3]",
                marked,
                flags=re.IGNORECASE
            )

        # 2. BƯỚC 2: Đánh dấu [P2] cho kết thúc câu (. ! ?) nếu chưa có [P3]
        # Tránh viết hoa sau dấu chấm của số thập phân (ví dụ 3.14)
        marked = re.sub(r"(?<!\d)([!?])\s*(?!\[P[1-3]\])", r"\1 [P2] ", marked)
        marked = re.sub(r"(?<!\d)\.(?!\d)\s*(?!\[P[1-3]\])", r". [P2] ", marked)

        # 3. BƯỚC 3: Đánh dấu [P1] cho dấu phẩy, chấm phẩy, hai chấm
        marked = re.sub(r"([,;:])\s*(?!\[P[1-3]\])", r"\1 [P1] ", marked)

        # 4. BƯỚC 4: Đánh dấu [P1] sau các từ nối tư duy nếu sau nó chưa có dấu phẩy hoặc pause
        for conn in self.DISCOURSE_CONNECTIVES:
            marked = re.sub(
                f"({conn})(?!\s*[,;:\.!?\[P])",
                r"\1 [P1]",
                marked,
                flags=re.IGNORECASE
            )

        # Dọn dẹp khoảng trắng kép và thẻ pause trùng lặp
        marked = re.sub(r"\[P1\]\s*\[P[23]\]", "[P2]", marked)
        marked = re.sub(r"\[P2\]\s*\[P3\]", "[P3]", marked)
        marked = re.sub(r"\[P1\]\s*\[P1\]+", "[P1]", marked)
        marked = re.sub(r"\s+", " ", marked).strip()

        # Đếm số lượng pause
        p1_count = len(re.findall(r"\[P1\]", marked))
        p2_count = len(re.findall(r"\[P2\]", marked))
        p3_count = len(re.findall(r"\[P3\]", marked))

        # Tính tổng thời gian nghỉ (giây)
        pause_total_s = round(
            (p1_count * (self.p1_ms / 1000.0)) +
            (p2_count * (self.p2_ms / 1000.0)) +
            (p3_count * (self.p3_ms / 1000.0)),
            2
        )

        # Tạo clean_speech_text (bỏ các nhãn [P1], [P2], [P3] để đọc hoặc làm phụ đề)
        clean_speech = re.sub(r"\[P[1-3]\]", "", marked)
        clean_speech = re.sub(r"\s+", " ", clean_speech).strip()

        words = len(clean_speech.split())
        speech_dur_s = round(words / wps, 2) if wps > 0 else 0.0
        calibrated_dur_s = round(speech_dur_s + pause_total_s, 2)

        # Sinh mã chuẩn W3C SSML
        ssml = marked
        ssml = ssml.replace("[P1]", f'<break time="{self.p1_ms}ms"/>')
        ssml = ssml.replace("[P2]", f'<break time="{self.p2_ms}ms"/>')
        ssml = ssml.replace("[P3]", f'<break time="{self.p3_ms}ms"/>')
        ssml_full = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="vi-VN">\n  <p>\n    {ssml}\n  </p>\n</speak>'

        return PlannedBeat(
            raw_text=text,
            marked_text=marked,
            ssml_text=ssml_full,
            clean_speech_text=clean_speech,
            word_count=words,
            p1_count=p1_count,
            p2_count=p2_count,
            p3_count=p3_count,
            pause_total_s=pause_total_s,
            speech_duration_s=speech_dur_s,
            calibrated_duration_s=calibrated_dur_s
        )

    def calculate_calibrated_duration(self, text: str, custom_wpm: int | None = None) -> float:
        """Hàm tiện ích lấy nhanh thời lượng chuẩn xác (giây)."""
        return self.plan(text, custom_wpm).calibrated_duration_s


# Khởi tạo singleton dùng nhanh
prosody_planner = ProsodyPlanner()
