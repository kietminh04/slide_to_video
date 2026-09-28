"""Hybrid Analyzer: LLM Text-Only Semantic Understanding.

Thay vì gửi ảnh (VLM, ~15K tokens/slide), module này gửi TEXT THUẦN (~300-800 tokens/slide)
cho LLM để phân tích ngữ cảnh sư phạm.

Pipeline:
  HybridExtractor → structured markdown → HybridAnalyzer (text-only LLM) → JSON cấu trúc

Tiết kiệm token: ~90% so với VLM thuần
  - VLM: 13 slides × ~15K tokens = ~200K tokens
  - Hybrid: 13 slides × ~800 tokens = ~10K tokens
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

# Hỗ trợ cả SDK mới (google-genai) lẫn SDK cũ (google-generativeai)
_GENAI_TYPE = None
try:
    from google import genai
    _GENAI_TYPE = "new"
except ImportError:
    try:
        import google.generativeai as legacy_genai
        _GENAI_TYPE = "legacy"
    except ImportError:
        _GENAI_TYPE = None


class HybridAnalyzer:
    """Phân tích ngữ cảnh sư phạm từ text đã parse (không dùng ảnh)."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.client = None

        if _GENAI_TYPE and self.api_key:
            try:
                if _GENAI_TYPE == "new":
                    self.client = genai.Client(api_key=self.api_key)
                elif _GENAI_TYPE == "legacy":
                    legacy_genai.configure(api_key=self.api_key)
                    self.client = legacy_genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"[HybridAnalyzer] Không thể khởi tạo Gemini client: {e}")
                self.client = None

        self.system_prompt = """Bạn là chuyên gia phân tích bài giảng đại học. 
Dựa vào nội dung TEXT đã được trích xuất từ slide bên dưới, hãy phân tích và trả về JSON:
{
  "slide_number": <số>,
  "title": "Tiêu đề chính",
  "text_content": ["Nội dung chi tiết từng điểm..."],
  "math_formulas": ["Công thức LaTeX nếu có"],
  "visual_description": "Mô tả ngắn gọn cấu trúc/sơ đồ nếu slide có chứa hình",
  "key_concepts": ["Khái niệm 1", "Khái niệm 2"],
  "teaching_notes": "Gợi ý giảng dạy cho giảng viên"
}

QUY TẮC:
1. Giữ nguyên mọi công thức toán, không thay đổi ký hiệu.
2. Phân tích MỐI QUAN HỆ giữa các điểm nội dung, không chỉ liệt kê lại.
3. Trường "teaching_notes" phải chứa gợi ý SƯ PHẠM thực sự (nên nhấn mạnh gì, ví dụ minh họa nào).
4. Nếu nội dung chỉ là "[Slide có chứa hình ảnh/sơ đồ]" → ghi nhận trong visual_description.
5. Chỉ trả về JSON hợp lệ, KHÔNG markdown formatting.
"""

    def _generate_text(self, prompt: str) -> str:
        """Thực hiện gọi LLM hỗ trợ cả SDK mới và cũ."""
        if not self.client:
            raise RuntimeError("Gemini client chưa được khởi tạo hoặc thiếu API key")

        if _GENAI_TYPE == "new":
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return resp.text or ""
        elif _GENAI_TYPE == "legacy":
            resp = self.client.generate_content(prompt)
            return resp.text or ""
        raise RuntimeError("Không có thư viện LLM nào sẵn sàng")

    def analyze_slide(self, structured_text: str, slide_number: int) -> Dict:
        """Phân tích một slide từ text đã parse — KHÔNG GỬI ẢNH.

        Args:
            structured_text: Markdown đã cấu trúc từ HybridExtractor
            slide_number: Số thứ tự slide

        Returns:
            Dict chứa kết quả phân tích JSON
        """
        try:
            prompt = (
                f"{self.system_prompt}\n\n"
                f"--- NỘI DUNG SLIDE {slide_number} (ĐÃ PARSE TỪ OCR & LAYOUT) ---\n"
                f"{structured_text}\n"
                f"--- HẾT NỘI DUNG ---"
            )

            text_resp = self._generate_text(prompt).strip()

            # Loại bỏ markdown code blocks
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            if text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]

            result = json.loads(text_resp.strip())
            result["slide_number"] = slide_number

            return result

        except json.JSONDecodeError as e:
            print(f"[Hybrid] Lỗi parse JSON slide {slide_number}: {e}")
            return self._fallback_from_text(structured_text, slide_number)
        except Exception as e:
            print(f"[Hybrid] Lỗi phân tích slide {slide_number}: {e}")
            return self._fallback_from_text(structured_text, slide_number)

    def analyze_batch(
        self, slides_text: List[str], start_number: int = 1, batch_size: int = 5
    ) -> List[Dict]:
        """Phân tích nhiều slide gộp thành 1 request để tiết kiệm thêm token.

        Thay vì 13 requests × ~800 tokens = 13 requests,
        gộp 5 slides/request → chỉ 3 requests.

        Args:
            slides_text: List markdown text của từng slide
            start_number: Slide bắt đầu
            batch_size: Số slide gộp mỗi batch

        Returns:
            List[Dict] kết quả phân tích
        """
        all_results = []

        for i in range(0, len(slides_text), batch_size):
            batch = slides_text[i:i + batch_size]
            batch_start = start_number + i

            try:
                combined = "\n\n---\n\n".join(
                    f"=== SLIDE {batch_start + j} ===\n{text}"
                    for j, text in enumerate(batch)
                )

                prompt = (
                    f"{self.system_prompt}\n\n"
                    f"Phân tích {len(batch)} slides sau đây. "
                    f"Trả về một JSON ARRAY chứa {len(batch)} objects, "
                    f"mỗi object theo đúng cấu trúc đã mô tả.\n\n"
                    f"--- BẮT ĐẦU NỘI DUNG ---\n{combined}\n--- HẾT NỘI DUNG ---"
                )

                text_resp = self._generate_text(prompt).strip()

                # Clean markdown formatting
                if text_resp.startswith("```json"):
                    text_resp = text_resp[7:]
                if text_resp.startswith("```"):
                    text_resp = text_resp[3:]
                if text_resp.endswith("```"):
                    text_resp = text_resp[:-3]

                parsed = json.loads(text_resp.strip())

                if isinstance(parsed, list):
                    for j, item in enumerate(parsed):
                        item["slide_number"] = batch_start + j
                    all_results.extend(parsed)
                elif isinstance(parsed, dict):
                    parsed["slide_number"] = batch_start
                    all_results.append(parsed)

            except Exception as e:
                print(f"[Hybrid] Lỗi batch {i//batch_size + 1}: {e}, fallback từng slide")
                # Fallback: phân tích từng slide riêng lẻ
                for j, text in enumerate(batch):
                    result = self.analyze_slide(text, batch_start + j)
                    all_results.append(result)

        return all_results

    def _fallback_from_text(self, structured_text: str, slide_number: int) -> Dict:
        """Trích xuất cơ bản từ text khi LLM fail — không mất dữ liệu."""
        lines = structured_text.split("\n")
        title = ""
        text_content = []
        formulas = []
        key_concepts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("### ") or line.startswith("#### "):
                candidate = line.lstrip("#").strip()
                if not title:
                    title = candidate
                else:
                    key_concepts.append(candidate)
            elif line.startswith("$$") or "∑" in line or "∫" in line:
                formulas.append(line.replace("$$", "").strip())
            elif line.startswith("- "):
                text_content.append(line[2:])
            elif not line.startswith("*[") and not line.startswith("## Slide"):
                text_content.append(line)

        return {
            "slide_number": slide_number,
            "title": title or f"Slide {slide_number}",
            "text_content": text_content,
            "math_formulas": formulas,
            "visual_description": "",
            "key_concepts": key_concepts,
            "teaching_notes": ""
        }
