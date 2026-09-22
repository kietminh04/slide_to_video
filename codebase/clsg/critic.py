"""Agent Phản biện & Đánh giá Chất lượng (Critic & Quality Guard Agent).

Tự động phán xét kịch bản trên 4 trục định lượng:
1. Trục Pacing (Độ bám thời lượng / Ngân sách từ)
2. Trục Terminology (Độ tuân thủ thuật ngữ Glossary tiếng Việt)
3. Trục Grounding (Chống ảo giác / Bằng chứng nguồn)
4. Trục Visual Alignment (Độ tương thích chỉ dẫn thị giác)
"""

from __future__ import annotations

import re
from codebase.clsg.config import Settings
from codebase.clsg.glossary import PedagogicalGlossary
from codebase.clsg.schemas import (
    Blueprint,
    Chunk,
    CriticScorecard,
    Script,
)


class CriticAgent:
    """Agent phản biện độc lập trong hệ sinh thái Multi-Agent."""

    def __init__(self, glossary: PedagogicalGlossary | None = None, settings: Settings | None = None):
        self.glossary = glossary or PedagogicalGlossary()
        self.settings = settings

    def evaluate(self, script: Script, blueprint: Blueprint, chunks: list[Chunk]) -> CriticScorecard:
        """Thực hiện đánh giá toàn diện kịch bản và xuất bảng điểm CriticScorecard."""
        chunk_ids = {c.id for c in chunks}
        critique_items: list[str] = []

        # === 1. Đánh giá Trục Pacing ===
        target_words_map = {seg.chapter: seg.word_budget for seg in blueprint.segments}
        pacing_deviations: list[float] = []

        for scene in script.scenes:
            actual_words = sum(len(b.display_text.split()) for b in scene.beats)
            target_words = target_words_map.get(scene.chapter, 140)
            dev = abs(actual_words - target_words) / target_words if target_words > 0 else 0.0
            pacing_deviations.append(dev)

            if dev > 0.15:
                direction = "nói thừa" if actual_words > target_words else "nói quá ngắn thiếu"
                critique_items.append(
                    f"Pacing: Phân cảnh {scene.id} {direction} ({actual_words}/{target_words} từ, sai số {dev:.1%}). Cần co giãn lại."
                )

        avg_dev = sum(pacing_deviations) / len(pacing_deviations) if pacing_deviations else 0.0
        pacing_score = max(0.0, min(100.0, 100.0 - (avg_dev * 100.0)))

        # === 2. Đánh giá Trục Terminology & Ngôn ngữ ===
        all_text = " ".join(b.display_text for s in script.scenes for b in s.beats)
        audit_res = self.glossary.audit_terminology(all_text)
        terminology_score = audit_res["tcr_score"]

        for viol in audit_res["violations"][:5]:  # Lấy tối đa 5 lỗi tiêu biểu
            critique_items.append(f"Thuật ngữ: Phát hiện {viol}.")

        # === 3. Đánh giá Trục Grounding (Chống ảo giác) ===
        invalid_source_count = 0
        total_claims = 0

        for scene in script.scenes:
            for b_idx, beat in enumerate(scene.beats):
                if beat.type == "claim":
                    total_claims += 1
                    if not beat.source_ids:
                        invalid_source_count += 1
                        critique_items.append(f"Ảo giác: Phân cảnh {scene.id}, nhịp {b_idx} là claim nhưng không có source_id.")
                    else:
                        for sid in beat.source_ids:
                            if sid not in chunk_ids:
                                invalid_source_count += 1
                                critique_items.append(f"Ảo giác: source_id '{sid}' không có trong tài liệu slide nguồn.")

        if total_claims > 0:
            grounding_score = max(0.0, 100.0 - (invalid_source_count / total_claims * 100.0))
        else:
            grounding_score = 100.0

        # === 4. Đánh giá Trục Visual Alignment ===
        valid_visual_count = 0
        valid_visual_types = {
            "zoom_in", "split_screen", "highlight_box", "animated_diagram",
            "equation_solve", "timeline_bar", "code_walkthrough", "side_by_side_compare",
            "flowchart_reveal", "concept_map", "metric_callout", "headline_takeover",
            "ambient_decorative", "process_visualization", "equation", "diagram", "title+bullets"
        }

        for scene in script.scenes:
            v_type = (scene.visual.visual_type or scene.visual.layout or "").lower()
            if any(vt in v_type for vt in valid_visual_types):
                valid_visual_count += 1
            else:
                critique_items.append(f"Visual: Phân cảnh {scene.id} chưa có loại thị giác chuẩn Taxonomy.")

        visual_score = (valid_visual_count / len(script.scenes) * 100.0) if script.scenes else 100.0

        # === Tổng hợp điểm số (Weighted Overall Score) ===
        overall_score = round(
            0.35 * pacing_score +
            0.30 * terminology_score +
            0.25 * grounding_score +
            0.10 * visual_score,
            2
        )

        passed = overall_score >= 85.0 and avg_dev <= 0.15 and len(audit_res["violations"]) == 0

        return CriticScorecard(
            pacing_score=round(pacing_score, 2),
            terminology_score=round(terminology_score, 2),
            grounding_score=round(grounding_score, 2),
            visual_score=round(visual_score, 2),
            overall_score=overall_score,
            passed=passed,
            feedback=critique_items
        )
