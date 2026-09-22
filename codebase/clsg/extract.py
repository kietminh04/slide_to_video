"""Trích xuất tài liệu đa định dạng (PPTX, PDF, DOCX, TXT) thành danh sách Chunk.

Sử dụng thuật toán bóc tách cấu trúc hình học (Zero-Vision Geometric Extractor)
sắp xếp theo thứ tự đọc tự nhiên (top -> bottom, left -> right).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from codebase.clsg.schemas import Chunk


def extract(path: Path) -> list[Chunk]:
    """Trích xuất tài liệu thành danh sách Chunk phân cấp."""
    suffix = path.suffix.lower()

    if suffix == ".pptx":
        return _extract_pptx(path)
    elif suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".txt", ".md"):
        return _extract_txt(path)
    elif suffix == ".docx":
        return _extract_docx(path)

    raise NotImplementedError(
        f"Chưa hỗ trợ định dạng {suffix}. Hỗ trợ: .pptx, .pdf, .docx, .txt, .md"
    )


def _extract_pptx(path: Path) -> list[Chunk]:
    """Trích xuất slide PowerPoint sử dụng cấu trúc tọa độ 2D của python-pptx."""
    from pptx import Presentation

    prs = Presentation(str(path))
    chunks: list[Chunk] = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        chapter_id = f"ch{slide_idx}"
        slide_title = ""
        slide_texts: list[str] = []

        # Sắp xếp các shape theo trục dọc (top) và trục ngang (left)
        sorted_shapes = sorted(
            [s for s in slide.shapes if s.has_text_frame or s.has_table],
            key=lambda s: (s.top or 0, s.left or 0)
        )

        chunk_counter = 0

        # Tìm tiêu đề slide
        if slide.shapes.title and slide.shapes.title.text.strip():
            slide_title = slide.shapes.title.text.strip()
            chunk_counter += 1
            chunks.append(
                Chunk(
                    id=f"c_{chapter_id}_{chunk_counter:02d}",
                    chapter=chapter_id,
                    text=f"[TIÊU ĐỀ SLIDE {slide_idx}]: {slide_title}",
                    page=slide_idx,
                    kind="text",
                    needs_human=False
                )
            )

        for shape in sorted_shapes:
            if shape == slide.shapes.title:
                continue

            if shape.has_text_frame:
                text = shape.text.strip()
                if text and text != slide_title:
                    chunk_counter += 1
                    chunks.append(
                        Chunk(
                            id=f"c_{chapter_id}_{chunk_counter:02d}",
                            chapter=chapter_id,
                            text=text,
                            page=slide_idx,
                            kind="text",
                            needs_human=False
                        )
                    )
            elif shape.has_table:
                table_lines = []
                for row in shape.table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells]
                    table_lines.append(" | ".join(row_cells))
                if table_lines:
                    chunk_counter += 1
                    chunks.append(
                        Chunk(
                            id=f"c_{chapter_id}_{chunk_counter:02d}",
                            chapter=chapter_id,
                            text="BẢNG DỮ LIỆU:\n" + "\n".join(table_lines),
                            page=slide_idx,
                            kind="table",
                            needs_human=False
                        )
                    )

        # Nếu slide không có chữ nào (chỉ có hình)
        if chunk_counter == 0:
            chunks.append(
                Chunk(
                    id=f"c_{chapter_id}_01",
                    chapter=chapter_id,
                    text=f"[Slide {slide_idx}: Nội dung trực quan / Hình ảnh minh họa]",
                    page=slide_idx,
                    kind="caption",
                    needs_human=True
                )
            )

    return chunks


def _extract_pdf(path: Path) -> list[Chunk]:
    """Trích xuất tài liệu PDF theo từng trang sử dụng PyMuPDF / fitz."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    chunks: list[Chunk] = []

    for page_idx, page in enumerate(doc, start=1):
        chapter_id = f"ch{page_idx}"
        text = page.get_text("text").strip()
        needs_human = len(text) < 30

        chunks.append(
            Chunk(
                id=f"c_{chapter_id}_01",
                chapter=chapter_id,
                text=text if text else f"[Trang PDF {page_idx}: Đồ họa hoặc bảng vẽ]",
                page=page_idx,
                kind="text",
                needs_human=needs_human
            )
        )

    doc.close()
    return chunks


def _extract_docx(path: Path) -> list[Chunk]:
    """Trích xuất văn bản Word (.docx) theo từng mục Heading."""
    from docx import Document

    doc = Document(str(path))
    chunks: list[Chunk] = []
    current_chapter = "ch1"
    current_paras: list[str] = []
    chapter_idx = 1
    chunk_counter = 0

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue

        if p.style.name.startswith("Heading"):
            if current_paras:
                chunk_counter += 1
                chunks.append(
                    Chunk(
                        id=f"c_{current_chapter}_{chunk_counter:02d}",
                        chapter=current_chapter,
                        text="\n".join(current_paras),
                        kind="text",
                    )
                )
                current_paras = []
            chapter_idx += 1
            current_chapter = f"ch{chapter_idx}"
            chunk_counter = 0
            chunks.append(
                Chunk(
                    id=f"c_{current_chapter}_01",
                    chapter=current_chapter,
                    text=f"[MỤC]: {txt}",
                    kind="text"
                )
            )
        else:
            current_paras.append(txt)

    if current_paras:
        chunk_counter += 1
        chunks.append(
            Chunk(
                id=f"c_{current_chapter}_{chunk_counter:02d}",
                chapter=current_chapter,
                text="\n".join(current_paras),
                kind="text",
            )
        )

    return chunks


def _extract_txt(path: Path) -> list[Chunk]:
    """Trích xuất từ file text thuần hoặc Markdown."""
    text = path.read_text(encoding="utf-8")
    chunks: list[Chunk] = []
    current_chapter = "ch0"
    current_text_lines: list[str] = []
    chunk_counter = 0

    for line in text.split("\n"):
        if line.strip().startswith("## Chương") or line.strip().startswith("## Slide") or line.strip().startswith("# "):
            if current_text_lines:
                chunk_counter += 1
                chunks.append(
                    Chunk(
                        id=f"c_{current_chapter}_{chunk_counter:02d}",
                        chapter=current_chapter,
                        text="\n".join(current_text_lines).strip(),
                    )
                )
                current_text_lines = []

            # Trích tên chương: "## Chương 1: Giới thiệu" -> "ch1"
            m = re.search(r"(?:Chương|Slide)\s*(\d+)", line, re.IGNORECASE)
            if m:
                current_chapter = f"ch{m.group(1)}"
            else:
                chunk_counter += 1
                current_chapter = f"ch{chunk_counter}"
            chunk_counter = 0

        current_text_lines.append(line)

    if current_text_lines:
        chunk_counter += 1
        chunks.append(
            Chunk(
                id=f"c_{current_chapter}_{chunk_counter:02d}",
                chapter=current_chapter,
                text="\n".join(current_text_lines).strip(),
            )
        )

    return chunks
