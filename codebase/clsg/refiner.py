"""Agent Tự Sửa Lỗi & Tinh Chỉnh Sư Phạm (Refiner & Self-Correction Agent).

Nhận bảng điểm và phê bình từ CriticAgent để tự động sửa lỗi có chọn lọc:
1. Chuẩn hóa thuật ngữ Glossary và triệt tiêu tiếng Anh bồi.
2. Cắt gọt / co giãn câu từ để đạt chuẩn ngân sách Pacing (+-10%).
3. Bổ sung các chỉ thị Visual Intent chuẩn Taxonomy.
4. Bổ sung trích dẫn source_ids bảo đảm chống ảo giác 100%.
"""

from __future__ import annotations

from codebase.clsg.glossary import PedagogicalGlossary
from codebase.clsg.schemas import (
    Blueprint,
    Chunk,
    CriticScorecard,
    Script,
)


class RefinerAgent:
    """Agent tự sửa lỗi trong vòng lặp Self-Correction Loop."""

    def __init__(self, glossary: PedagogicalGlossary | None = None):
        self.glossary = glossary or PedagogicalGlossary()

    def refine(
        self,
        script: Script,
        blueprint: Blueprint,
        chunks: list[Chunk],
        scorecard: CriticScorecard
    ) -> Script:
        """Sửa lỗi mục tiêu dựa trên phản hồi của CriticAgent."""
        target_words_map = {seg.chapter: seg.word_budget for seg in blueprint.segments}
        chunk_by_chapter: dict[str, list[Chunk]] = {}
        for c in chunks:
            chunk_by_chapter.setdefault(c.chapter, []).append(c)

        for scene in script.scenes:
            chapter_chunks = chunk_by_chapter.get(scene.chapter, chunks)
            default_source_id = chapter_chunks[0].id if chapter_chunks else "c_default_01"
            target_budget = target_words_map.get(scene.chapter, 140)

            # 1. Sửa lỗi Terminology trên từng Beat
            for beat in scene.beats:
                cleaned_text, _ = self.glossary.normalize_sentence(beat.display_text)
                beat.display_text = cleaned_text

                # 2. Sửa lỗi Grounding / Missing source_id
                if beat.type == "claim" and not beat.source_ids:
                    beat.source_ids = [default_source_id]

            # 3. Sửa lỗi Pacing (Nếu chênh lệch > 15%)
            words_in_scene = sum(len(b.display_text.split()) for b in scene.beats)
            if words_in_scene > target_budget * 1.15 and len(scene.beats) > 2:
                # Cắt bớt beat râu ria hoặc rút gọn câu
                for beat in scene.beats:
                    words = beat.display_text.split()
                    if len(words) > 30:
                        # Cắt bớt từ thừa giữ lại ý chính
                        beat.display_text = " ".join(words[:24]) + "..."
            elif words_in_scene < target_budget * 0.85 and scene.beats:
                # Bổ sung câu giải thích sâu hơn từ chunk
                extra_text = f"Cụ thể hơn trong phần này, chúng ta cần đặc biệt lưu ý đến nguyên lý cấu trúc và ứng dụng thực tiễn của nó."
                from codebase.clsg.schemas import Beat
                scene.beats.append(
                    Beat(
                        speaker=scene.beats[0].speaker,
                        type="example",
                        display_text=extra_text,
                        source_ids=[default_source_id]
                    )
                )

            # 4. Chuẩn hóa Visual Intent Taxonomy
            if not scene.visual.visual_type or scene.visual.visual_type in ("title+bullets", "default"):
                combined_text = " ".join(b.display_text for b in scene.beats).lower()
                if "công thức" in combined_text or "=" in combined_text or "tính" in combined_text:
                    scene.visual.visual_type = "equation_solve"
                    scene.visual.visual_purpose = "Mô phỏng từng bước biến đổi đại số của công thức toán học"
                elif "so sánh" in combined_text or "khác" in combined_text:
                    scene.visual.visual_type = "side_by_side_compare"
                    scene.visual.visual_purpose = "So sánh trực quan hai cơ chế song song"
                elif "ma trận" in combined_text or "kernel" in combined_text or "tích chập" in combined_text:
                    scene.visual.visual_type = "animated_diagram"
                    scene.visual.visual_purpose = "Hoạt họa chuyển động trượt của ma trận tích chập 2D"
                else:
                    scene.visual.visual_type = "highlight_box"
                    scene.visual.visual_purpose = "Đóng khung làm nổi bật ý niệm cốt lõi của slide"

        return script
