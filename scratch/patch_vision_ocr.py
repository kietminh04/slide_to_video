import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

# Prompt cho Vision OCR (Lấy từ backend/services/vision_analyzer.py hoặc tạo một cái xịn)
PROMPT = """Bạn là Kỹ sư Trưởng Giáo dục AI (Chief AI Education Engineer). 
Nhiệm vụ của bạn là bóc tách toàn bộ file ảnh slide bài giảng thành cây tri thức chuẩn sư phạm (Bridge-Core-Deep).

YÊU CẦU ĐẦU RA (DUY NHẤT TRẢ VỀ JSON HỢP LỆ):
{
  "total_pages": <tổng số slide>,
  "chapters": [
    {
      "chapter": "CHƯƠNG 1",
      "title": "Tên chương",
      "visual_type": "split_screen",
      "sections": [
        {
          "code": "1.1",
          "title": "Tên phần",
          "items": [
            {
              "code": "1.1.1",
              "pdfStart": <số thứ tự ảnh bắt đầu (từ 1)>,
              "pdfEnd": <số thứ tự ảnh kết thúc>,
              "details": "Nội dung chi tiết text bóc tách từ ảnh...",
              "examples": "Ví dụ minh họa nếu có...",
              "mechanism": "Công thức toán học hoặc quy trình...",
              "summary": "Tóm tắt...",
              "key_point": "Điểm then chốt..."
            }
          ]
        }
      ]
    }
  ]
}
BẮT BUỘC: pdfStart và pdfEnd phải chính xác theo thứ tự ảnh (từ 1 đến tổng số ảnh). Không được tự bịa ra thông tin không có trong ảnh. Đảm bảo cấu trúc JSON hợp lệ hoàn toàn.
"""

# Hàm JS mới
REPLACEMENT = """    async function extractVisualSlideStructure(file) {
      updateLoading("Đang phân tích ảnh slide bằng Vision AI...", "Đang quét và chuyển đổi slide thành hình ảnh...");
      
      const cfg = LLMClient.getConfig();
      if (!cfg.apiKey) {
          showToast("❌ Bạn cần nhập API Key (Gemini/OpenAI) trong phần Cấu Hình Chung để dùng tính năng Vision OCR trên trình duyệt.");
          hideLoading();
          return null;
      }
      
      try {
        // 1. Dùng pdf.js để chuyển đổi các trang PDF thành ảnh Base64
        if (typeof pdfjsLib === 'undefined') {
          console.warn('[Vision OCR] pdf.js chưa tải xong');
          throw new Error("Thư viện PDF chưa sẵn sàng");
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        const buf = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
        const totalPages = pdf.numPages;
        
        // Giới hạn số trang quét để tránh payload quá to (OpenAI/Gemini thường nhận tối đa vài chục MB)
        const scanLimit = Math.min(totalPages, 50); 
        const imageParts = [];
        
        for (let p = 1; p <= scanLimit; p++) {
          updateLoading("Đang quét trang...", `Trang ${p} / ${scanLimit}`);
          const page = await pdf.getPage(p);
          const viewport = page.getViewport({ scale: 1.5 }); // Scale 1.5 đủ nét cho OCR
          
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          canvas.height = viewport.height;
          canvas.width = viewport.width;
          
          await page.render({ canvasContext: ctx, viewport: viewport }).promise;
          const base64Img = canvas.toDataURL('image/jpeg', 0.85);
          
          imageParts.push({
             type: "image_url",
             image_url: { url: base64Img }
          });
        }
        
        updateLoading("Đang gửi lên máy chủ AI...", `Phân tích ${scanLimit} ảnh slide bằng ${cfg.model}...`);
        
        const endpoint = `${cfg.baseUrl.replace(/\\/+$/, '')}/chat/completions`;
        const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${cfg.apiKey}` };
        
        const promptText = `""" + PROMPT.replace('\n', '\\n') + """`;
        
        const payload = {
          model: cfg.model,
          messages: [
            {
              role: "user",
              content: [
                { type: "text", text: promptText },
                ...imageParts
              ]
            }
          ],
          max_tokens: 4000,
          temperature: 0.2
        };
        
        const res = await fetch(endpoint, {
           method: 'POST',
           headers: headers,
           body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`API Error HTTP ${res.status}: ${errText.substring(0, 150)}`);
        }
        
        const data = await res.json();
        const raw = data.choices?.[0]?.message?.content || '';
        const parsed = LLMClient.safeJsonParse(raw);
        
        if (parsed && parsed.chapters && parsed.chapters.length > 0) {
           hideLoading();
           return {
              title: (file.name || '').replace(/\\.[^/.]+$/, ""),
              totalPages: totalPages, // Số trang thật của PDF
              chapters: parsed.chapters,
              method: 'vision-ocr-frontend'
           };
        } else {
           throw new Error("AI không trả về cấu trúc hợp lệ.");
        }
      } catch (err) {
        console.error("Lỗi extractVisualSlideStructure:", err);
        showToast("❌ Lỗi Vision OCR: " + err.message);
      }
      hideLoading();
      return null;
    }"""

# Thay thế hàm cũ
target_start_marker = "async function extractVisualSlideStructure(file) {"
target_end_marker = "async function extractDocumentStructure(file) {"

start_idx = content.find(target_start_marker)
end_idx = content.find(target_end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + REPLACEMENT + "\n\n    " + content[end_idx:]
    with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patched successfully!")
else:
    print("Could not find the function boundaries.")
