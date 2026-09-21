import json
from typing import Any

from codebase.clsg.schemas import Chunk, Script

# Giả định LLMProvider có phương thức generate_structured hoặc tương tự.
# Vì không biết chính xác API, ta có thể nhận một callable hoặc interface giả định.

class BaselineGenerator:
    """Tạo kịch bản bằng một prompt duy nhất (baseline)."""

    def __init__(self, llm_provider: Any):
        self.llm = llm_provider

    def generate(self, doc_id: str, chunks: list[Chunk], weights: dict[str, float] = None) -> Script:
        """Sinh kịch bản bằng 1 cú gọi LLM."""
        weights = weights or {}

        # Tạo prompt gộp toàn bộ text
        context = "\n".join(
            f"--- CHUNK {c.id} (Chương {c.chapter}) ---\n{c.text}" for c in chunks
        )

        prompt = f"""
Bạn là một chuyên gia viết kịch bản video học thuật.
Dựa vào tài liệu sau, hãy viết một kịch bản video dài khoảng 5 phút.

YÊU CẦU:
- Phân bổ nội dung theo trọng số các chương: {json.dumps(weights, ensure_ascii=False)}
- Trích xuất các sự kiện, dẫn chứng rõ ràng.
- Đảm bảo định dạng chuẩn đầu ra theo schema yêu cầu.

TÀI LIỆU:
{context}
"""

        # Gọi LLM, ép về schema Script.
        # Giả sử llm_provider có hàm generate_structured(prompt, schema)
        if hasattr(self.llm, "generate_structured"):
            result = self.llm.generate_structured(prompt, Script)
            if isinstance(result, Script):
                return result

        # Nếu LLMProvider trả về dict hoặc chuỗi JSON:
        if hasattr(self.llm, "generate_json"):
            result_data = self.llm.generate_json(prompt)
            return Script.model_validate(result_data)

        # Dạng gọi mặc định
        if hasattr(self.llm, "__call__"):
            result_data = self.llm(prompt, schema=Script)
            if isinstance(result_data, Script):
                return result_data
            return Script.model_validate(result_data)

        raise NotImplementedError("Không rõ cách gọi LLMProvider để lấy schema Script")
        try:
            return self.llm.generate(prompt=prompt, response_model=Script, step="baseline")
        except Exception as e:
            raise RuntimeError(f"Lỗi khi chạy baseline: {e}") from e
