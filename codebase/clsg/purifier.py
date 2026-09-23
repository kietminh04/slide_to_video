"""Module ContentPurifier: Làm sạch và chuẩn hóa văn bản bài giảng 3 tầng.

Được thiết kế theo tiêu chuẩn sư phạm CIKM 2025:
- Tầng 1: Lọc rác cấu trúc (Header/Footer, số trang, ngày tháng, copyright lặp lại).
- Tầng 2: Bóc tách nhãn đạo diễn/prompt (HOOK, S1, Lời thoại, Câu hỏi gợi mở) thành metadata.
- Tầng 3: Chuẩn hóa glyph & ký âm tiếng Việt cho TTS (Unicode NFKC, bullet to pauses, toán học).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PurifiedText:
    """Kết quả sau khi làm sạch văn bản."""
    clean_text: str
    pedagogical_roles: list[str] = field(default_factory=list)
    removed_artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentPurifier:
    """Bộ lọc rác và chuẩn hóa văn bản sư phạm 3 tầng."""

    # TẦNG 2: Regex nhận diện các token đạo diễn / prompt leakage
    ROLE_PATTERNS = [
        (r"\[?(?:HOOK|DẪN NHẬP|MỞ ĐẦU)\]?:?\s*", "HOOK"),
        (r"\[?(?:INTRO|GIỚI THIỆU)\]?:?\s*", "INTRO"),
        (r"\[?(?:DEEP_DIVE|ĐI SÂU|PHÂN TÍCH KỸ)\]?:?\s*", "DEEP_DIVE"),
        (r"\[?(?:CORE|NỘI DUNG CHÍNH|TRỌNG TÂM)\]?:?\s*", "CORE"),
        (r"\[?(?:SUMMARY|TỔNG KẾT|KẾT LUẬN|OUTRO)\]?:?\s*", "SUMMARY"),
        (r"(?:\[S\d+\]|(?<![A-Za-z0-9])S\d+:|SCENE_\d+|PHÂN CẢNH\s*\d+):?\s*", "SCENE_MARKER"),
        (r"(?:\[BEAT_\d+\]|(?<![A-Za-z0-9])BEAT_\d+|NHỊP\s*\d+):?\s*", "BEAT_MARKER"),
        (r"\*\*(?:Người dẫn|Giảng viên|Teacher|MC|Lời thoại|Kịch bản):\*\*\s*", "SPEAKER_TAG"),
        (r"(?:HÃY SUY NGHĨ|LƯU Ý QUAN TRỌNG|CÂU HỎI GỢI MỞ|ĐẶT VẤN ĐỀ):\s*", "THINKING_PROMPT"),
    ]

    # TẦNG 3: Bảng chuyển đổi Bullet Symbols thành dấu câu tự nhiên
    BULLET_REPLACEMENTS = {
        "■": ", ",
        "□": ", ",
        "●": ", ",
        "○": ", ",
        "◆": ", ",
        "◇": ", ",
        "➢": ", ",
        "▶": ", ",
        "►": ", ",
        "▪": ", ",
        "▫": ", ",
        "–": " - ",
        "—": " - ",
        "•": ", ",
        "\u2022": ", ",
        "\u25aa": ", ",
        "\u25cf": ", ",
    }

    # Bảng phiên âm ký tự toán học & đơn vị cơ bản sang tiếng Việt
    MATH_TRANSLATIONS = [
        (r"\b%\b|(?<=\d)%", " phần trăm"),
        (r"\bapprox\b|\$\\approx\$|≈", " xấp xỉ "),
        (r"\bleq\b|\$\\le\$|\$\\leq\$|≤|<= ", " nhỏ hơn hoặc bằng "),
        (r"\bgeq\b|\$\\ge\$|\$\\geq\$|≥|>= ", " lớn hơn hoặc bằng "),
        (r"\bne\b|\$\\ne\$|\$\\neq\$|≠|!= ", " khác "),
        (r"(?<=\s)>\s*", " lớn hơn "),
        (r"(?<=\s)<\s*", " nhỏ hơn "),
        (r"\$\\sum\$|∑", " tổng "),
        (r"\$\\in\$|∈", " thuộc "),
        (r"\$\\pm\$|±", " cộng trừ "),
        (r"\$\\times\$|×", " nhân "),
    ]

    def __init__(self, repeat_threshold: float = 0.5):
        """
        Args:
            repeat_threshold: Tỉ lệ lặp lại (>=50%) để coi 1 dòng là header/footer rác.
        """
        self.repeat_threshold = repeat_threshold

    # =========================================================================
    # TẦNG 1: LỌC RÁC CẤU TRÚC VÀ METADATA TỰ ĐỘNG
    # =========================================================================
    def clean_document_pages(self, pages_text: list[str]) -> list[str]:
        """Quét toàn bộ tài liệu để tìm và loại bỏ Header/Footer lặp lại theo thống kê."""
        if not pages_text:
            return []

        total_pages = len(pages_text)
        if total_pages <= 1:
            return [self.clean_single_text(p) for p in pages_text]

        # 1. Thống kê tần suất xuất hiện của các dòng đầu tiên và dòng cuối cùng
        top_lines = []
        bottom_lines = []
        for text in pages_text:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                top_lines.append(lines[0])
                if len(lines) > 1:
                    bottom_lines.append(lines[-1])

        top_counter = Counter(top_lines)
        bottom_counter = Counter(bottom_lines)

        repeated_headers = {
            line for line, count in top_counter.items()
            if count / total_pages >= self.repeat_threshold and len(line) < 120
        }
        repeated_footers = {
            line for line, count in bottom_counter.items()
            if count / total_pages >= self.repeat_threshold and len(line) < 120
        }

        # 2. Làm sạch từng trang
        cleaned_pages = []
        for text in pages_text:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            filtered_lines = []
            for idx, line in enumerate(lines):
                # Bỏ header lặp
                if idx == 0 and line in repeated_headers:
                    continue
                # Bỏ footer lặp
                if idx == len(lines) - 1 and line in repeated_footers:
                    continue
                # Bỏ số trang: "Trang 1/35", "Page 2 of 30", "Slide 12", "- 15 -"
                if re.match(r"^(?:trang|page|slide)?\s*-?\s*\d+\s*(?:/\s*\d+|of\s*\d+)?\s*-?$", line, re.I):
                    continue
                # Bỏ copyright notice
                if re.search(r"©|all rights reserved|confidential|chỉ lưu hành nội bộ", line, re.I):
                    continue
                # Bỏ timestamp / ngày tháng đơn độc
                if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", line):
                    continue

                filtered_lines.append(line)

            page_cleaned = "\n".join(filtered_lines)
            cleaned_pages.append(self.clean_single_text(page_cleaned))

        return cleaned_pages

    # =========================================================================
    # TẦNG 2 & 3: LỌC NHÃN ĐẠO DIỄN VÀ CHUẨN HÓA KÝ ÂM CHO 1 ĐOẠN VĂN BẢN
    # =========================================================================
    def purify(self, raw_text: str) -> PurifiedText:
        """Làm sạch toàn diện 1 đoạn văn bản hoặc lời thoại bài giảng."""
        if not raw_text:
            return PurifiedText(clean_text="")

        text = raw_text
        detected_roles: list[str] = []
        removed: list[str] = []

        # 1. Unicode NFKC normalization
        text = unicodedata.normalize("NFKC", text)

        # 2. TẦNG 2: Bóc tách nhãn đạo diễn / prompt tags
        for pattern, role_name in self.ROLE_PATTERNS:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                detected_roles.append(role_name)
                removed.extend(matches)
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Loại bỏ các tag markdown lồng như **Lời thoại:** hoặc [GIẢNG VIÊN]
        text = re.sub(r"\[(?:HOOK|S\d+|EXPLAIN|NOTE|DẪN NHẬP)\]", "", text, flags=re.IGNORECASE)

        # Loại bỏ các dòng số trang và copyright lẫn trong đoạn
        lines = []
        for line in text.splitlines():
            l_strip = line.strip()
            if re.match(r"^(?:trang|page|slide)?\s*-?\s*\d+\s*(?:/\s*\d+|of\s*\d+)?\s*-?$", l_strip, re.I):
                removed.append(l_strip)
                continue
            if re.search(r"©|all rights reserved|confidential|chỉ lưu hành nội bộ", l_strip, re.I):
                removed.append(l_strip)
                continue
            lines.append(line)
        text = "\n".join(lines)

        # 3. TẦNG 3: Thay thế Bullet Symbols thành ngắt câu tự nhiên
        for sym, repl in self.BULLET_REPLACEMENTS.items():
            if sym in text:
                text = text.replace(sym, repl)

        # Phiên âm toán học cơ bản cho TTS
        for pattern, repl in self.MATH_TRANSLATIONS:
            text = re.sub(pattern, repl, text)

        # 4. Chuẩn hóa khoảng trắng & dấu câu tiếng Việt
        # Xóa dấu phẩy / dấu chấm lặp dính nhau (ví dụ: ",,", ".,", ", .")
        text = re.sub(r"[,;:\-]\s*[,;:\-]+", ", ", text)
        text = re.sub(r"\.\s*\.+", ".", text)
        text = re.sub(r"\s+([,.;?!])", r"\1", text)  # đưa dấu câu sát từ trước
        text = re.sub(r"([,.;?!])(?=[^\s\d])", r"\1 ", text)  # sau dấu câu phải có khoảng trắng

        # Gọt khoảng trắng thừa
        text = re.sub(r"[ \t]+", " ", text).strip()
        # Chuẩn hóa đầu dòng
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        final_text = "\n".join(lines)

        return PurifiedText(
            clean_text=final_text,
            pedagogical_roles=list(set(detected_roles)),
            removed_artifacts=removed,
            metadata={"word_count": len(final_text.split())}
        )

    def clean_single_text(self, text: str) -> str:
        """Hàm tiện ích trả về chuỗi sạch trực tiếp."""
        return self.purify(text).clean_text


# Khởi tạo singleton dùng nhanh
purifier = ContentPurifier()
