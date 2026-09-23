from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from codebase.clsg.config import Settings
from codebase.clsg.llm import LLMProvider
from codebase.clsg.schemas import (
    Blueprint,
    Chunk,
    ClaimCheck,
    FactSheet,
    GuardReport,
    Script,
)


class JudgeResult(BaseModel):
    checks: list[ClaimCheck] = Field(default_factory=list)


class Guard:
    """Module kiểm tra chất lượng kịch bản."""

    def __init__(self, llm: LLMProvider, settings: Settings):
        self.llm = llm
        self.settings = settings

        template_dir = Path(__file__).parent / "prompts"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def check_script(
        self,
        script: Script,
        blueprint: Blueprint,
        chunks: list[Chunk],
        fact_sheets: dict[str, FactSheet]
    ) -> GuardReport:
        """Thực hiện các kiểm tra và trả về báo cáo GuardReport."""
        # 1. Missing sources
        chunk_ids = {c.id for c in chunks}
        missing_sources = set()
        for scene in script.scenes:
            for beat in scene.beats:
                for sid in beat.source_ids:
                    if sid not in chunk_ids:
                        missing_sources.add(sid)

        # 2. Pacing và L1 allocation
        pacing_dev = {}
        target_words_map = {seg.chapter: seg.word_budget for seg in blueprint.segments}
        target_weight_map = {seg.chapter: seg.weight for seg in blueprint.segments}

        actual_words_map = {}
        total_actual_words = 0

        for scene in script.scenes:
            words = sum(len(beat.display_text.split()) for beat in scene.beats)
            actual_words_map[scene.chapter] = words
            total_actual_words += words

            target_words = target_words_map.get(scene.chapter, 0)
            if target_words > 0:
                pacing_dev[scene.id] = abs(words - target_words) / target_words
            else:
                pacing_dev[scene.id] = 0.0

        allocation_l1 = 0.0
        if total_actual_words > 0:
            for chapter in target_weight_map:
                target_w = target_weight_map[chapter]
                actual_w = actual_words_map.get(chapter, 0) / total_actual_words
                allocation_l1 += abs(actual_w - target_w)

        # 3. Depth check
        depth_ok = {}
        for scene in script.scenes:
            if scene.depth == "deep":
                fs = fact_sheets.get(scene.chapter)
                used_facts = set()
                has_number_or_example = False

                for beat in scene.beats:
                    for fid in beat.fact_ids:
                        used_facts.add(fid)
                        if fs and 0 <= fid < len(fs.facts):
                            kind = fs.facts[fid].kind
                            if kind in ("number", "example"):
                                has_number_or_example = True

                ok = len(used_facts) >= self.settings.min_facts_deep and has_number_or_example
                depth_ok[scene.id] = ok
            else:
                depth_ok[scene.id] = True

        # 4. LLM Judge cho claims
        claims = []
        for scene in script.scenes:
            for i, beat in enumerate(scene.beats):
                if beat.type == "claim":
                    claims.append({
                        "scene_id": scene.id,
                        "beat_index": i,
                        "text": beat.display_text
                    })

        claim_checks = []
        if claims:
            template = self.env.get_template("judge.j2")
            prompt = template.render(chunks=chunks, claims=claims)

            result = self.llm.generate(
                prompt=prompt,
                response_model=JudgeResult,
                model=self.settings.model_judge,
                step="guard_judge"
            )
            claim_checks = result.checks

        # Kiểm tra điều kiện passed
        passed = True
        if missing_sources:
            passed = False

        for dev in pacing_dev.values():
            if dev > self.settings.pacing_threshold:
                passed = False

        if allocation_l1 > self.settings.allocation_l1_threshold:
            passed = False

        if not all(depth_ok.values()):
            passed = False

        for check in claim_checks:
            if check.verdict != "supported":
                passed = False

        return GuardReport(
            pacing_dev=pacing_dev,
            allocation_l1=allocation_l1,
            missing_sources=sorted(list(missing_sources)),
            depth_ok=depth_ok,
            claim_checks=claim_checks,
            passed=passed,
            rounds=0
        )


class ActiveRescaler:
    """Bộ điều phối cân bằng thời lượng động (Active Rescaler).
    
    Tự động co giãn WPM, điều chỉnh nhịp ngắt và nén từ đệm để triệt tiêu
    sai số thời lượng, đưa độ lệch thực tế về ngưỡng <= 5% (chuẩn MOOC).
    """

    FILLER_PHRASES = [
        r"\bnhư chúng ta đã biết\b,?\s*",
        r"\bcó thể thấy rằng\b,?\s*",
        r"\bthực tế cho thấy là\b,?\s*",
        r"\bở đây chúng ta thấy\b,?\s*",
        r"\brõ ràng là\b,?\s*",
        r"\bvề cơ bản thì\b,?\s*",
    ]

    @classmethod
    def auto_rescale(
        cls,
        script: Script,
        target_duration_s: float,
        base_wpm: int = 140,
        max_allowed_error: float = 0.05
    ) -> tuple[Script, dict]:
        """Tự động bù trừ và điều phối timeline để đạt độ chính xác <= 5%."""
        from codebase.clsg.prosody import ProsodyPlanner

        planner = ProsodyPlanner(wpm=base_wpm)

        # 1. Tính tổng thời lượng calibrated ban đầu
        total_initial_s = 0.0
        all_beats = [b for s in script.scenes for b in s.beats]
        
        for beat in all_beats:
            res = planner.plan(beat.display_text, custom_wpm=base_wpm)
            beat.est_s = res.calibrated_duration_s
            beat.tts_text = res.marked_text
            total_initial_s += res.calibrated_duration_s

        if target_duration_s <= 0:
            target_duration_s = total_initial_s or 300.0

        initial_error = abs(total_initial_s - target_duration_s) / target_duration_s
        actions_taken = []
        current_wpm = base_wpm

        # 2. Nếu sai số > 5%, tiến hành bù trừ chủ động
        adjusted_total_s = total_initial_s

        if initial_error > max_allowed_error:
            ratio = total_initial_s / target_duration_s

            if ratio > 1.05:
                # Kịch bản bị dài hơn ngân sách -> Cần rút ngắn
                # B1: Tăng WPM nhẹ trong khoảng cho phép [140 -> 155]
                target_wpm = min(155, int(base_wpm * min(ratio, 1.12)))
                current_wpm = target_wpm
                actions_taken.append(f"Tăng nhịp độ đọc WPM từ {base_wpm} lên {current_wpm}")

                # B2: Nếu vẫn quá dài (> 1.15), gọt bỏ các từ đệm không mang nghĩa
                if ratio > 1.15:
                    import re
                    trimmed_count = 0
                    for beat in all_beats:
                        old_text = beat.display_text
                        for fp in cls.FILLER_PHRASES:
                            beat.display_text = re.sub(fp, "", beat.display_text, flags=re.I)
                        if beat.display_text != old_text:
                            trimmed_count += 1
                    if trimmed_count > 0:
                        actions_taken.append(f"Gọt bỏ từ đệm trên {trimmed_count} nhịp thoại")

                # B3: Co nhẹ khoảng lặng (pause) [0.85x]
                planner = ProsodyPlanner(
                    wpm=current_wpm,
                    p1_ms=int(ProsodyPlanner.DEFAULT_P1_MS * 0.85),
                    p2_ms=int(ProsodyPlanner.DEFAULT_P2_MS * 0.85),
                    p3_ms=int(ProsodyPlanner.DEFAULT_P3_MS * 0.85)
                )

            elif ratio < 0.95:
                # Kịch bản bị ngắn hơn ngân sách -> Cần kéo dài thời gian
                # B1: Giảm WPM nhẹ trong khoảng cho phép [130 -> 140]
                target_wpm = max(130, int(base_wpm * max(ratio, 0.92)))
                current_wpm = target_wpm
                actions_taken.append(f"Giảm nhịp độ đọc WPM từ {base_wpm} xuống {current_wpm} để học viên kịp tiếp thu")

                # B2: Giãn khoảng lặng tư duy và quan sát slide [1.25x]
                planner = ProsodyPlanner(
                    wpm=current_wpm,
                    p1_ms=int(ProsodyPlanner.DEFAULT_P1_MS * 1.2),
                    p2_ms=int(ProsodyPlanner.DEFAULT_P2_MS * 1.25),
                    p3_ms=int(ProsodyPlanner.DEFAULT_P3_MS * 1.3)
                )
                actions_taken.append("Giãn thời gian dừng quan sát slide [P3] và nhịp ngắt tư duy")

        # 3. Phân bổ lại timeline liên tục cho toàn bộ scenes và beats
        t_cursor = 0.0
        for scene in script.scenes:
            scene.t_start = round(t_cursor, 2)
            for beat in scene.beats:
                res = planner.plan(beat.display_text, custom_wpm=current_wpm)
                beat.est_s = res.calibrated_duration_s
                beat.tts_text = res.marked_text
                t_cursor += res.calibrated_duration_s
            scene.t_end = round(t_cursor, 2)

        # 4. Nếu vẫn còn thiếu thời gian, phân bổ khoảng lặng ngắm nhìn slide (Slide Coda Pause)
        gap = target_duration_s - t_cursor
        if gap > 0 and len(script.scenes) > 0 and (gap / target_duration_s) > max_allowed_error:
            coda_per_scene = round(gap / len(script.scenes), 2)
            t_cursor = 0.0
            for scene in script.scenes:
                scene.t_start = round(t_cursor, 2)
                for beat in scene.beats:
                    t_cursor += beat.est_s
                if scene.beats:
                    scene.beats[-1].est_s += coda_per_scene
                    scene.beats[-1].prosody.pause_after_ms += int(coda_per_scene * 1000)
                    scene.beats[-1].tts_text += f" [P3]"
                    t_cursor += coda_per_scene
                scene.t_end = round(t_cursor, 2)
            actions_taken.append(f"Thêm khoảng lặng chiêm nghiệm slide cuối mỗi phân cảnh (+{coda_per_scene}s/cảnh)")

        final_duration_s = round(t_cursor, 2)
        final_error = abs(final_duration_s - target_duration_s) / target_duration_s

        rescaling_meta = {
            "target_duration_s": target_duration_s,
            "initial_duration_s": round(total_initial_s, 2),
            "final_duration_s": final_duration_s,
            "initial_error_pct": round(initial_error * 100, 2),
            "final_error_pct": round(final_error * 100, 2),
            "calibrated_wpm": current_wpm,
            "actions_taken": actions_taken,
            "passed_dar_p": final_error <= max_allowed_error
        }

        return script, rescaling_meta

