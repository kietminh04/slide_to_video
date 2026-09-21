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
