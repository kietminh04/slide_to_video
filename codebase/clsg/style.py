"""Khoác phong cách lên kịch bản đã qua guard.

Module này là khung – sẽ được hoàn thiện theo Prompt 5.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from codebase.clsg.config import Settings
from codebase.clsg.llm import LLMProvider
from codebase.clsg.schemas import Beat, Script


class StyledSceneResult(BaseModel):
    beats: list[Beat]


class TruthCheckResult(BaseModel):
    is_same_meaning: bool
    reason: str


def apply_style(
    script: Script,
    pack_name: str,
    llm: LLMProvider,
    settings: Settings,
) -> Script:
    """Khoác phong cách lên kịch bản.

    Ràng buộc:
    - Không đổi nghĩa beat claim
    - Chỉ thêm beat flavor (tối đa 20% số từ) và viết lại câu nối
    - Sau style chạy lại guard sự thật

    Args:
        script: Kịch bản đã qua guard.
        pack_name: Tên style pack (VD: 'serious', 'drama_tongtai').
        llm: LLM provider.
        settings: Cấu hình pipeline.

    Returns:
        Script đã khoác phong cách.
    """
    # 1. Load style pack
    pack_path = Path(f"codebase/clsg/packs/{pack_name}.yaml")
    if not pack_path.exists():
        raise ValueError(f"Style pack '{pack_name}' không tồn tại tại {pack_path}")

    with open(pack_path, "r", encoding="utf-8") as f:
        pack_data = yaml.safe_load(f)

    # 2. Setup Jinja2
    env = Environment(loader=FileSystemLoader("codebase/clsg/prompts"))
    try:
        template = env.get_template("style.j2")
    except Exception:
        # Fallback if template doesn't exist
        template = env.from_string(
            "Style pack: {{ pack_name }}\n"
            "Khuôn: {{ storytelling_template }}\n"
            "Beats:\n"
            "{% for beat in beats %}[{{ beat.type }}] {{ beat.display_text }}\n{% endfor %}\n"
        )

    judge_template = env.from_string(
        "Kiểm tra xem câu [Sau] có giữ nguyên sự thật và ý nghĩa cốt lõi của câu [Trước] không.\n"
        "Trước: {{ original }}\n"
        "Sau: {{ styled }}\n"
        "Chỉ cần khác biệt về phong cách, không được bóp méo thông tin học thuật."
    )

    new_script = copy.deepcopy(script)

    for i, scene in enumerate(new_script.scenes):
        if not scene.beats:
            continue

        # Render prompt for the scene
        prompt = template.render(
            pack_name=pack_name,
            storytelling_template=pack_data.get("storytelling_template", ""),
            examples=pack_data.get("examples", []),
            beats=scene.beats,
        )

        try:
            # Generate styled scene
            result = llm.generate(
                prompt=prompt,
                response_model=StyledSceneResult,
                model=settings.model_generator,
                step=f"style_{scene.id}",
            )
        except Exception:
            # If generation fails, keep original
            continue

        # Validate constraints
        # Constraint 1: Flavor words <= 20%
        total_words = sum(len(b.display_text.split()) for b in result.beats)
        flavor_words = sum(len(b.display_text.split()) for b in result.beats if b.type == "flavor")

        if total_words > 0 and flavor_words / total_words > settings.max_flavor_ratio:
            # Violated flavor ratio constraint, keep original scene
            continue

        # Constraint 2 & 3: Match claims and check truth
        original_claims = [b for b in scene.beats if b.type == "claim"]
        styled_claims = [b for b in result.beats if b.type == "claim"]

        if len(original_claims) != len(styled_claims):
            # Lost or added claims, keep original scene
            continue

        # Truth check for each claim
        claims_ok = True
        for orig, styled in zip(original_claims, styled_claims):
            judge_prompt = judge_template.render(
                original=orig.display_text,
                styled=styled.display_text,
            )
            try:
                judge_res = llm.generate(
                    prompt=judge_prompt,
                    response_model=TruthCheckResult,
                    model=settings.model_judge,
                    step=f"judge_{scene.id}",
                )
                if not judge_res.is_same_meaning:
                    claims_ok = False
                    break
            except Exception:
                # If judge fails, fail safe (keep original)
                claims_ok = False
                break

        if claims_ok:
            # Keep original source_ids and properties for claims
            # Ensure we don't lose necessary meta
            for orig, styled in zip(original_claims, styled_claims):
                styled.source_ids = orig.source_ids
                styled.fact_ids = orig.fact_ids
            scene.beats = result.beats

    # Update script meta
    new_script.meta.style = pack_name
    return new_script
