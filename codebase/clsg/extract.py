"""Trích xuất tài liệu (PPTX, DOCX, PDF) thành danh sách Chunk.

Module này chưa được triển khai – sẽ do người phụ trách extract hoàn thiện.
"""

from __future__ import annotations

from pathlib import Path

from codebase.clsg.schemas import Chunk


def extract(path: Path) -> list[Chunk]:
    """Trích xuất tài liệu thành danh sách Chunk.

    Args:
        path: Đường dẫn tới tài liệu (PPTX, DOCX, PDF, TXT).

    Returns:
        Danh sách Chunk đã trích xuất.

    Raises:
        NotImplementedError: Chưa triển khai cho định dạng thật.
    """
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return _extract_txt(path)

    raise NotImplementedError(
        f"Chưa hỗ trợ định dạng {suffix}. "
        f"Sẽ triển khai: .pptx, .docx, .pdf"
    )


def _extract_txt(path: Path) -> list[Chunk]:
    """Trích xuất từ file text thuần – dùng cho fixture và test.

    Quy ước: dòng bắt đầu bằng '## Chương' là ranh giới chương.
    """
    text = path.read_text(encoding="utf-8")
    chunks: list[Chunk] = []
    current_chapter = "ch0"
    current_text_lines: list[str] = []
    chunk_counter = 0

    for line in text.split("\n"):
        if line.strip().startswith("## Chương"):
            # Lưu chunk trước đó
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

            # Tìm số chương
            parts = line.strip().split(":")
            chapter_part = parts[0].replace("## Chương", "").strip()
            try:
                ch_num = int(chapter_part)
                current_chapter = f"ch{ch_num}"
            except ValueError:
                current_chapter = f"ch{len(chunks) + 1}"
            chunk_counter = 0
        else:
            if line.strip():
                current_text_lines.append(line)

    # Chunk cuối
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
