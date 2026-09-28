"""Hybrid Extractor: High-Level Parsing (OCR + Layout Analysis).

Kiến trúc 3 tầng:
  Tầng 1 — Raw Text Extraction: PyMuPDF vector text → Windows OCR fallback cho trang scan
  Tầng 2 — Layout Analysis: Phân loại block (tiêu đề, bullet, bảng, công thức, caption)
  Tầng 3 — Structured Markdown: Đóng gói thành chuỗi text có cấu trúc ngữ nghĩa

Ưu điểm so với VLM thuần:
  - Giảm ~90% token (gửi text ~500 tokens thay vì ảnh ~15K tokens/slide)
  - Tốc độ nhanh hơn 5-10x (không cần encode/decode ảnh base64)
  - Chi phí API giảm tỷ lệ thuận
"""

from __future__ import annotations

import io
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class TextBlock:
    """Một khối văn bản đã được phân loại layout."""
    text: str
    kind: str  # "title", "bullet", "paragraph", "table", "formula", "caption", "code"
    font_size: float = 0.0
    is_bold: bool = False
    bbox: tuple = (0, 0, 0, 0)  # (x0, y0, x1, y1)
    page: int = 0


@dataclass
class ParsedSlide:
    """Kết quả parse một trang/slide."""
    page_number: int
    title: str = ""
    blocks: list[TextBlock] = field(default_factory=list)
    has_images: bool = False
    has_tables: bool = False
    raw_text: str = ""

    def to_structured_markdown(self) -> str:
        """Chuyển đổi thành chuỗi markdown có cấu trúc để gửi cho LLM."""
        parts = [f"## Slide {self.page_number}"]

        if self.title:
            parts.append(f"### {self.title}")

        for block in self.blocks:
            if block.kind == "title" and block.text != self.title:
                parts.append(f"#### {block.text}")
            elif block.kind == "bullet":
                parts.append(f"- {block.text}")
            elif block.kind == "formula":
                parts.append(f"$$\n{block.text}\n$$")
            elif block.kind == "table":
                parts.append(block.text)
            elif block.kind == "caption":
                parts.append(f"*[Hình: {block.text}]*")
            elif block.kind == "code":
                parts.append(f"```\n{block.text}\n```")
            else:
                parts.append(block.text)

        if self.has_images and not any(b.kind == "caption" for b in self.blocks):
            parts.append("*[Slide có chứa hình ảnh/sơ đồ minh họa]*")

        return "\n\n".join(parts)


class HybridExtractor:
    """Bóc tách nội dung tài liệu bằng High-Level Parsing."""

    # Ngưỡng phân loại
    TITLE_FONT_RATIO = 1.3       # Font lớn hơn 130% trung bình → tiêu đề
    MIN_TEXT_FOR_OCR = 30         # Dưới 30 ký tự → cần OCR
    BULLET_PATTERNS = re.compile(
        r'^[\s]*[•●○◆◇▪▸►▹→\-–—\*]\s+|'      # Bullet Unicode
        r'^[\s]*\d+[\.\)]\s+|'                   # Numbered list
        r'^[\s]*[a-zA-Z][\.\)]\s+|'              # Lettered list
        r'^[\s]*\([a-zA-Z0-9]+\)\s+'             # Parenthetical list
    )
    FORMULA_PATTERNS = re.compile(
        r'[∑∏∫∂∇∞±√≈≠≤≥∈∉⊂⊃∪∩∀∃]|'            # Ký tự toán học Unicode
        r'\\(?:frac|sum|int|sqrt|alpha|beta|gamma|theta|sigma|lambda|omega|hat|bar|vec|dot)|'
        r'\$[^$]+\$|'                              # Inline LaTeX
        r'[A-Za-z]+\s*[=<>≥≤]\s*[A-Za-z0-9\(\)]'  # Phương trình đại số đơn giản
    )

    def extract_from_pdf(self, file_bytes: bytes) -> list[ParsedSlide]:
        """Bóc tách PDF bằng PyMuPDF text + layout analysis + OCR fallback."""
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        slides = []

        for page_idx, page in enumerate(doc, start=1):
            parsed = self._parse_pdf_page(page, page_idx)
            slides.append(parsed)

        doc.close()
        return slides

    def extract_from_pptx(self, file_bytes: bytes) -> list[ParsedSlide]:
        """Bóc tách PPTX bằng python-pptx geometric extraction."""
        from pptx import Presentation
        from pptx.util import Pt

        prs = Presentation(io.BytesIO(file_bytes))
        slides = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            parsed = ParsedSlide(page_number=slide_idx)

            # Lấy tiêu đề
            if slide.shapes.title and slide.shapes.title.text.strip():
                parsed.title = slide.shapes.title.text.strip()

            # Sắp xếp shape theo thứ tự đọc tự nhiên (top → bottom, left → right)
            sorted_shapes = sorted(
                [s for s in slide.shapes if s.has_text_frame or s.has_table],
                key=lambda s: (s.top or 0, s.left or 0)
            )

            for shape in sorted_shapes:
                if shape == slide.shapes.title:
                    continue

                if shape.has_table:
                    parsed.has_tables = True
                    table_md = self._pptx_table_to_markdown(shape.table)
                    parsed.blocks.append(TextBlock(
                        text=table_md, kind="table", page=slide_idx
                    ))
                elif shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if not text or text == parsed.title:
                            continue

                        # Phân tích font
                        max_font_size = 0.0
                        is_bold = False
                        for run in para.runs:
                            if run.font.size:
                                fs = run.font.size.pt
                                if fs > max_font_size:
                                    max_font_size = fs
                            if run.font.bold:
                                is_bold = True

                        kind = self._classify_text_block(text, max_font_size, is_bold)
                        parsed.blocks.append(TextBlock(
                            text=text, kind=kind,
                            font_size=max_font_size, is_bold=is_bold,
                            page=slide_idx
                        ))

                # Kiểm tra hình ảnh
                if hasattr(shape, 'shape_type') and shape.shape_type == 13:
                    parsed.has_images = True

            # Kiểm tra shapes không có text (ảnh thuần)
            for shape in slide.shapes:
                if hasattr(shape, 'shape_type') and shape.shape_type == 13:
                    parsed.has_images = True
                    break

            parsed.raw_text = parsed.to_structured_markdown()
            slides.append(parsed)

        return slides

    def extract_from_docx(self, file_bytes: bytes) -> list[ParsedSlide]:
        """Bóc tách DOCX theo heading structure."""
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        slides = []
        current_slide = ParsedSlide(page_number=1)
        page_counter = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            if para.style.name.startswith("Heading"):
                # Mỗi heading = trang mới
                if current_slide.blocks or current_slide.title:
                    current_slide.raw_text = current_slide.to_structured_markdown()
                    slides.append(current_slide)
                    page_counter += 1
                    current_slide = ParsedSlide(page_number=page_counter)

                level = para.style.name.replace("Heading", "").strip()
                if level in ("1", "2"):
                    current_slide.title = text
                else:
                    current_slide.blocks.append(TextBlock(
                        text=text, kind="title", is_bold=True, page=page_counter
                    ))
            else:
                kind = self._classify_text_block(text, 0, False)
                current_slide.blocks.append(TextBlock(
                    text=text, kind=kind, page=page_counter
                ))

        # Flush slide cuối
        if current_slide.blocks or current_slide.title:
            current_slide.raw_text = current_slide.to_structured_markdown()
            slides.append(current_slide)

        # Trích xuất bảng
        for table in doc.tables:
            table_md = self._docx_table_to_markdown(table)
            if slides:
                slides[-1].blocks.append(TextBlock(
                    text=table_md, kind="table", page=len(slides)
                ))
                slides[-1].has_tables = True

        return slides

    # ──────────────────── INTERNAL METHODS ────────────────────

    def _parse_pdf_page(self, page, page_idx: int) -> ParsedSlide:
        """Parse một trang PDF: text vector + layout + OCR fallback."""
        import fitz

        parsed = ParsedSlide(page_number=page_idx)

        # Tầng 1: Trích text vector với thông tin font
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        text_blocks_raw = []

        for block in blocks:
            if block["type"] == 0:  # Text block
                current_para_lines = []
                current_font_size = 0.0
                current_bold = False

                def _flush_para():
                    nonlocal current_para_lines, current_font_size, current_bold
                    if current_para_lines:
                        full_text = " ".join(current_para_lines).strip()
                        if full_text:
                            text_blocks_raw.append(TextBlock(
                                text=full_text,
                                kind="paragraph",
                                font_size=current_font_size,
                                is_bold=current_bold,
                                bbox=tuple(block["bbox"]),
                                page=page_idx
                            ))
                        current_para_lines = []
                        current_font_size = 0.0
                        current_bold = False

                for line in block.get("lines", []):
                    line_text = ""
                    line_font_size = 0.0
                    line_bold = False
                    for span in line.get("spans", []):
                        line_text += span["text"]
                        if span["size"] > line_font_size:
                            line_font_size = span["size"]
                        if "bold" in span.get("font", "").lower() or "Bold" in span.get("font", ""):
                            line_bold = True

                    line_text = line_text.strip()
                    if not line_text:
                        continue

                    # Nếu là bullet hoặc tiêu đề độc lập -> flush paragraph trước đó
                    is_bullet = bool(self.BULLET_PATTERNS.match(line_text))
                    if is_bullet:
                        _flush_para()
                        text_blocks_raw.append(TextBlock(
                            text=line_text,
                            kind="bullet",
                            font_size=line_font_size,
                            is_bold=line_bold,
                            bbox=tuple(block["bbox"]),
                            page=page_idx
                        ))
                    else:
                        current_para_lines.append(line_text)
                        if line_font_size > current_font_size:
                            current_font_size = line_font_size
                        if line_bold:
                            current_bold = True

                _flush_para()
            elif block["type"] == 1:  # Image block
                parsed.has_images = True

        # Nếu text quá ít → OCR fallback
        total_text = " ".join(b.text for b in text_blocks_raw)
        if len(total_text) < self.MIN_TEXT_FOR_OCR:
            ocr_text = self._ocr_pdf_page(page)
            if ocr_text and len(ocr_text.strip()) > 10:
                # Parse OCR text đơn giản
                for line in ocr_text.split("\n"):
                    line = line.strip()
                    if line:
                        kind = self._classify_text_block(line, 0, False)
                        text_blocks_raw.append(TextBlock(
                            text=line, kind=kind, page=page_idx
                        ))

        if not text_blocks_raw:
            parsed.blocks.append(TextBlock(
                text=f"[Trang {page_idx}: Nội dung đồ họa/hình ảnh]",
                kind="caption", page=page_idx
            ))
            parsed.raw_text = parsed.to_structured_markdown()
            return parsed

        # Tầng 2: Layout Analysis — phân loại block
        avg_font = sum(b.font_size for b in text_blocks_raw if b.font_size > 0)
        count_font = sum(1 for b in text_blocks_raw if b.font_size > 0)
        avg_font = avg_font / count_font if count_font > 0 else 12.0

        for block in text_blocks_raw:
            block.kind = self._classify_text_block(
                block.text, block.font_size, block.is_bold,
                avg_font_size=avg_font
            )
            parsed.blocks.append(block)

        # Xác định tiêu đề trang (block đầu tiên dạng title)
        for block in parsed.blocks:
            if block.kind == "title":
                parsed.title = block.text
                break

        # Tầng 3: Merge thành structured markdown
        parsed.raw_text = parsed.to_structured_markdown()
        return parsed

    def _classify_text_block(
        self, text: str, font_size: float, is_bold: bool,
        avg_font_size: float = 12.0
    ) -> str:
        """Phân loại một block text thành category layout."""
        # Công thức toán học
        if self.FORMULA_PATTERNS.search(text):
            # Kiểm tra xem có phải câu bình thường chứa dấu = hay không
            if re.search(r'[∑∏∫∂∇∞±√≈≠≤≥∈∉⊂⊃∪∩∀∃]', text) or \
               text.count('=') > 1 or text.startswith('$'):
                return "formula"

        # Bullet point
        if self.BULLET_PATTERNS.match(text):
            return "bullet"

        # Tiêu đề (font lớn + bold, hoặc font lớn hơn 130% trung bình)
        if font_size > 0 and avg_font_size > 0:
            if font_size >= avg_font_size * self.TITLE_FONT_RATIO:
                return "title"
            if is_bold and font_size >= avg_font_size * 1.1:
                return "title"

        # Bold đơn lẻ ngắn → có thể là subtitle
        if is_bold and len(text) < 80:
            return "title"

        # Code block (nếu chứa nhiều ký tự đặc biệt lập trình)
        code_indicators = text.count('{') + text.count('}') + text.count(';') + \
                         text.count('def ') + text.count('class ') + text.count('//')
        if code_indicators >= 3:
            return "code"

        return "paragraph"

    def _ocr_pdf_page(self, page) -> str:
        """OCR fallback sử dụng Windows Media OCR (siêu nhanh, miễn phí)."""
        try:
            import winrt.windows.media.ocr as ocr_mod
            import winrt.windows.graphics.imaging as imaging
            import winrt.windows.storage as storage
            import asyncio
            import os
            import tempfile

            engine = ocr_mod.OcrEngine.try_create_from_user_profile_languages()
            if not engine:
                import winrt.windows.globalization as glob
                engine = ocr_mod.OcrEngine.try_create_from_language(
                    glob.Language('en-US')
                )
            if not engine:
                return ""

            async def _run():
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    pix = page.get_pixmap(dpi=150)
                    pix.save(tmp_path)
                    file = await storage.StorageFile.get_file_from_path_async(
                        os.path.abspath(tmp_path)
                    )
                    stream = await file.open_async(storage.FileAccessMode.READ)
                    decoder = await imaging.BitmapDecoder.create_async(stream)
                    bitmap = await decoder.get_software_bitmap_async()
                    res = await engine.recognize_async(bitmap)
                    return res.text
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            return asyncio.run(_run())
        except Exception:
            return ""

    def _pptx_table_to_markdown(self, table) -> str:
        """Chuyển bảng PPTX thành markdown table."""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace("|", "\\|") for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        if len(rows) >= 1:
            # Thêm separator sau header
            num_cols = len(table.rows[0].cells)
            separator = "| " + " | ".join(["---"] * num_cols) + " |"
            rows.insert(1, separator)
        return "\n".join(rows)

    def _docx_table_to_markdown(self, table) -> str:
        """Chuyển bảng DOCX thành markdown table."""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace("|", "\\|") for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        if len(rows) >= 1:
            num_cols = len(table.rows[0].cells)
            separator = "| " + " | ".join(["---"] * num_cols) + " |"
            rows.insert(1, separator)
        return "\n".join(rows)


def estimate_token_count(text: str) -> int:
    """Ước lượng số token cho text (tiếng Việt ~1.5 token/từ, tiếng Anh ~1.3 token/từ)."""
    words = text.split()
    # Heuristic: trung bình 1.4 token/từ cho text hỗn hợp Việt-Anh
    return int(len(words) * 1.4)
