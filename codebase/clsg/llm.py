"""LLM provider: interface, fake provider cho test, và OpenAI provider.

Mọi module nghiệp vụ nhận LLMProvider qua tham số, không khởi tạo bên trong.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Interface cho LLM – mọi thứ bên ngoài nằm sau interface này."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        response_model: type[T],
        model: str = "",
        step: str = "",
    ) -> T:
        """Gọi LLM và parse kết quả thành Pydantic model.

        Args:
            prompt: Prompt đã render (từ Jinja2 template).
            response_model: Pydantic model class để parse output.
            model: Tên model (mặc định lấy từ config).
            step: Tên bước pipeline (cho logging).

        Returns:
            Instance của response_model.
        """
        ...


class FakeLLMProvider(LLMProvider):
    """Provider giả cho test – trả kết quả cố định từ fixture.

    Không gọi API, không tốn tiền, CI an toàn.
    """

    def __init__(self, fixtures_dir: Path | None = None):
        self._fixtures_dir = fixtures_dir or Path("codebase/fixtures")
        self._call_count = 0

    def generate(
        self,
        prompt: str,
        response_model: type[T],
        model: str = "",
        step: str = "",
    ) -> T:
        """Trả kết quả mặc định dựa trên response_model."""
        self._call_count += 1
        # Tạo instance mặc định từ model – mỗi module sẽ
        # cung cấp fallback logic riêng khi LLM lỗi
        return self._make_default(response_model)

    def _make_default(self, model_class: type[T]) -> T:
        """Tạo instance với giá trị mặc định hợp lệ tối thiểu."""
        # Lấy thông tin field để tạo giá trị mặc định
        from codebase.clsg.schemas import (
            Beat,
            ClaimCheck,
            Fact,
            FactSheet,
            GuardReport,
            Scene,
            Script,
            ScriptMeta,
            TeachingPoint,
        )

        defaults: dict[type, dict[str, Any]] = {
            TeachingPoint: {
                "title": "Điểm dạy mặc định",
                "chunk_ids": ["c_0101"],
            },
            FactSheet: {
                "segment_chapter": "ch1",
                "facts": [
                    Fact(kind="definition", text="Định nghĩa mặc định", chunk_id="c_0101")
                ],
            },
            Scene: {
                "id": "s_fake",
                "chapter": "ch1",
                "depth": "core",
                "beats": [
                    Beat(
                        type="claim",
                        display_text="Nội dung mặc định từ FakeLLMProvider.",
                        source_ids=["c_0101"],
                    )
                ],
            },
            ClaimCheck: {
                "scene_id": "s_fake",
                "beat_index": 0,
                "verdict": "supported",
            },
            GuardReport: {
                "pacing_dev": {},
                "allocation_l1": 0.0,
                "missing_sources": [],
                "depth_ok": {},
                "claim_checks": [],
                "passed": True,
            },
            Script: {
                "meta": ScriptMeta(
                    doc_id="fake",
                    duration_s=300,
                    style="serious",
                    weights={"ch1": 1.0},
                ),
                "scenes": [],
            },
        }

        if model_class in defaults:
            return model_class(**defaults[model_class])

        # Fallback: thử tạo với giá trị rỗng
        try:
            return model_class()  # type: ignore[call-arg]
        except Exception:
            raise ValueError(
                f"FakeLLMProvider không biết cách tạo {model_class.__name__}. "
                f"Thêm vào defaults trong _make_default()."
            )


class OpenAIProvider(LLMProvider):
    """Provider dùng OpenAI API với structured output.

    Có cache đĩa theo hash và log usage ra JSONL.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        cache_dir: str = ".llm_cache",
        usage_log: str = "usage_log.jsonl",
        default_model: str = "gpt-4o",
    ):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._usage_log = Path(usage_log)
        self._default_model = default_model

    def generate(
        self,
        prompt: str,
        response_model: type[T],
        model: str = "",
        step: str = "",
    ) -> T:
        """Gọi OpenAI API, cache và log kết quả."""
        model = model or self._default_model
        schema_name = response_model.__name__

        # Kiểm tra cache
        cache_key = self._make_cache_key(prompt, model, schema_name)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return response_model.model_validate_json(cached)

        # Gọi API
        t0 = time.time()
        try:
            result = self._call_api(prompt, response_model, model)
            elapsed = time.time() - t0

            # Cache kết quả
            result_json = result.model_dump_json(indent=2)
            self._write_cache(cache_key, result_json)

            # Log thời gian thực tế
            self._log_usage(
                model=model, step=step or response_model.__name__,
                tokens_in=0, tokens_out=0, latency=elapsed,
            )

            return result
        except Exception as e:
            raise RuntimeError(f"Lỗi gọi LLM (step={step}, model={model}): {e}") from e

    def _call_api(self, prompt: str, response_model: type[T], model: str) -> T:
        """Gọi OpenAI API với structured output."""
        schema = response_model.model_json_schema()

        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            },
        )

        # Log usage
        usage = response.usage
        if usage:
            self._log_usage(
                model=model,
                step=response_model.__name__,
                tokens_in=usage.prompt_tokens,
                tokens_out=usage.completion_tokens,
                latency=0,  # sẽ được cập nhật ở generate()
            )

        # Parse response
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM trả về response rỗng")

        return response_model.model_validate_json(content)

    def _make_cache_key(self, prompt: str, model: str, schema_name: str) -> str:
        """Tạo cache key từ hash."""
        data = f"{prompt}|{model}|{schema_name}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _read_cache(self, key: str) -> str | None:
        """Đọc từ cache đĩa."""
        cache_file = self._cache_dir / f"{key}.json"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        return None

    def _write_cache(self, key: str, data: str) -> None:
        """Ghi vào cache đĩa."""
        cache_file = self._cache_dir / f"{key}.json"
        cache_file.write_text(data, encoding="utf-8")

    def _log_usage(
        self,
        model: str,
        step: str,
        tokens_in: int,
        tokens_out: int,
        latency: float,
    ) -> None:
        """Ghi log usage ra JSONL."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": model,
            "step": step,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_s": round(latency, 3),
        }
        with open(self._usage_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
