import json
import base64
from typing import List, Dict
import google.generativeai as genai
import os

class VisionAnalyzer:
    def __init__(self):
        # API key có thể lấy từ biến môi trường
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
        self.system_prompt = """
Bạn là chuyên gia phân tích bài giảng thị giác. Hãy quét kỹ bức ảnh slide này và trích xuất thông tin theo cấu trúc JSON:
{
  "slide_number": 1,
  "title": "Tiêu đề chính của slide",
  "text_content": [
    "Các gạch đầu dòng, định nghĩa, nội dung chi tiết..."
  ],
  "math_formulas": [
    "Công thức toán học dưới dạng LaTeX (ví dụ: $L = \\sum (y - \\hat{y})^2$)"
  ],
  "visual_description": "Mô tả ngắn gọn sơ đồ, hình vẽ, bảng biểu hoặc luồng kiến trúc có trong slide để giảng viên đưa vào kịch bản",
  "key_concepts": ["Khái niệm 1", "Khái niệm 2"]
}
Yêu cầu: Không bỏ sót chữ, giữ nguyên công thức toán, bỏ qua các chi tiết thừa như số trang hay watermark.
Chỉ trả về chuỗi JSON hợp lệ, không chứa markdown formatting như ```json.
"""

    def analyze_slide(self, image_bytes: bytes, slide_number: int) -> Dict:
        """Sử dụng Gemini Vision để phân tích một ảnh slide và trả về JSON."""
        try:
            image_parts = [
                {
                    "mime_type": "image/png",
                    "data": image_bytes
                }
            ]
            prompt = f"{self.system_prompt}\n\nĐây là slide số {slide_number}."
            
            response = self.model.generate_content([prompt, image_parts[0]])
            text_resp = response.text.strip()
            
            # Loại bỏ markdown code blocks nếu có
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            if text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]
                
            return json.loads(text_resp.strip())
        except Exception as e:
            print(f"Lỗi phân tích slide {slide_number}: {e}")
            return {
                "slide_number": slide_number,
                "title": f"Slide {slide_number}",
                "text_content": [],
                "math_formulas": [],
                "visual_description": "",
                "key_concepts": []
            }
