# CLSG Multi-Agent Studio Pro 🎬✨
### Configurable Lecture Script & Pedagogical Decision-Tree Studio
> **Tác giả:** Vũ Minh Kiệt (Toán Tin K67 - Đại học Bách khoa Hà Nội & VinAI / VinUni Khóa K4)  
> **Kho lưu trữ:** [github.com/kietminh04/slide_to_video](https://github.com/kietminh04/slide_to_video)  
> **Công nghệ:** Python 3.10+ • Vanilla JS / CSS Dark Glassmorphism • Web Speech API • PyMuPDF • Vercel Ready

---

## 🌟 Giới Thiệu Tổng Quan

**CLSG Multi-Agent Studio Pro** là nền tảng AI EdTech toàn diện chuyển đổi tài liệu bài giảng (Slide PowerPoint `.pptx`, tài liệu PDF `.pdf`, giáo trình Word `.docx`, văn bản `.txt`) thành **kịch bản video bài giảng chuẩn sư phạm MOOC** với cấu trúc phân cảnh chi tiết, nhịp độ WPM chuẩn xác và chỉ dẫn thị giác đồng bộ.

Hệ thống kết hợp tinh hoa thiết kế của **CVAT Projects Dashboard** (quản lý dự án dạng lưới thẻ) và **NotebookLM Workspace** (không gian phân tích nguồn học liệu đa kênh), mang đến trải nghiệm đồ họa hiện đại với giao diện **Dark Glassmorphism** mượt mà.

---

## 🚀 Các Tính Năng Đột Phá

1. **Bóc Tách Học Liệu Đa Phương Thức (Multi-Modal Extractor)**:
   - Tự động phân tích và trích xuất cấu trúc slide từ PDF (PyMuPDF / pdfjs), PowerPoint (python-pptx), Word (python-docx) mà không làm mất công thức toán học và bảng biểu.
2. **Cấu Hình AI Linh Hoạt (Gemini & OpenAI)**:
   - Hỗ trợ linh hoạt cả **Google Gemini** (Gemini 2.5 Pro, Flash) và **OpenAI** (GPT-4o, GPT-4o-mini).
   - Tùy chọn ngôn ngữ kịch bản: **Tiếng Việt Sư Phạm Chuẩn** hoặc **Tiếng Anh (English Academic)**.
3. **Cơ Chế Phân Bổ Thời Lượng & Chiều Sâu Sư Phạm (Dynamic Pedagogical Pacing)**:
   - Co giãn linh hoạt từ **5 phút đến 30 phút** (phân bổ từ 5 đến 30 phân cảnh động).
   - Kiểm soát tốc độ nói theo chuẩn **140 – 160 WPM** (theo nghiên cứu PACLIC 2023).
   - Cấu trúc nhận thức chuẩn: Khởi đầu bằng *Bridge* (cầu nối trực quan) $\to$ Thân bài *Core* (nguyên lý thuật toán) & *Deep* (tối ưu hóa tham số, hội tụ) $\to$ Kết thúc bằng *Bridge* (tổng kết, liên hệ thực tiễn).
4. **Từ Điển Thuật Ngữ Học Thuật LPM Engine (6.766 Thuật Ngữ)**:
   - Tự động chuẩn hóa từ mượn tiếng Anh sang tiếng Việt sư phạm (*clustering $\to$ phân cụm dữ liệu*, *gradient descent $\to$ hạ độ dốc*, *overfitting $\to$ quá khớp*).
5. **Teleprompter & Trình Nghe Thử Trực Tiếp (Inline Web Speech API)**:
   - Nghe thử giọng đọc tiếng Việt mượt mà ngay trên trình duyệt mà không tốn phí dịch vụ TTS đám mây.
   - Tự động cuộn trang và highlight câu thoại tương ứng theo thời gian thực.
6. **Xuất Đa Định Dạng Tức Thì**:
   - 📄 **Word (.docx):** Bảng kịch bản 4 cột chuẩn định dạng giáo án bộ môn.
   - 📝 **Markdown (.md):** Toàn văn transcript phân cảnh.
   - ⏱️ **Phụ đề (.srt):** Timestamp từng mili-giây khớp với giọng đọc.
   - 📊 **Cấu trúc (.json):** Toàn bộ metadata phục vụ dựng video tự động.

---

## 📂 Cấu Trúc Mã Nguồn

```
├── codebase/                 # Bộ lõi Multi-Agent Python
│   ├── clsg/
│   │   ├── config.py         # Cấu hình tham số WPM & thời lượng
│   │   ├── engine.py         # Điều phối pipeline Multi-Agent
│   │   ├── extract.py        # Extractor Agent (PDF, PPTX, DOCX)
│   │   ├── glossary.py       # LPM Glossary Engine (6.766 thuật ngữ)
│   │   ├── guard.py          # Bộ lọc chất lượng & an toàn nội dung
│   │   ├── llm.py            # Giao diện kết nối LLM (Gemini, OpenAI)
│   │   ├── prosody.py        # Bộ xử lý nhịp điệu & khoảng dừng W3C SSML
│   │   ├── purifier.py       # Làm sạch metadata rác
│   │   └── studio_generator.py # Bộ sinh kịch bản chi tiết theo phân đoạn
├── studio/                   # Giao diện Studio Web (Zero-build SPA)
│   ├── index.html            # Dark Glassmorphism Studio đầy đủ tính năng
│   └── server.py             # Python HTTP Server đa luồng (CORS + PNA)
├── index.html                # Trang chủ phục vụ triển khai Vercel (Zero-config)
├── vercel.json               # Cấu hình triển khai tự động lên Vercel
├── Dockerfile                # Đóng gói container Docker
├── pyproject.toml            # Quản lý dependencies (uv / pip)
└── README.md
```

---

## ⚡ Hướng Dẫn Chạy Cục Bộ (Local Deployment)

### Cách 1: Khởi động Studio nhanh (Khuyên dùng)
```bash
# 1. Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
# hoặc dùng uv:
uv sync

# 2. Khởi chạy máy chủ Studio
python studio/server.py

# 3. Mở trình duyệt tại:
http://localhost:8765
```

### Cách 2: Mở trực tiếp trên Trình Duyệt (Serverless Mode)
Chỉ cần mở tệp `studio/index.html` trực tiếp bằng trình duyệt Google Chrome hoặc Microsoft Edge. Hệ thống hỗ trợ bóc tách tài liệu và gọi API Gemini/OpenAI trực tiếp từ giao diện web!

---

## ☁️ Triển Khai Lên Vercel (Deploy to Vercel)

Dự án đã tích hợp sẵn tệp cấu hình `vercel.json`. Bạn có thể triển khai lên Vercel miễn phí chỉ trong 1 phút:

1. **Đăng nhập vào [vercel.com](https://vercel.com)** bằng tài khoản GitHub của bạn.
2. Bấm **"Add New..."** $\to$ **"Project"**.
3. Chọn kho lưu trữ **`kietminh04/slide_to_video`** và bấm **"Import"**.
4. Giữ nguyên toàn bộ cấu hình mặc định (Framework Preset: `Other`, Root Directory: `./`).
5. Bấm **"Deploy"**.
6. Sau 10–20 giây, trang web của bạn sẽ hoạt động trực tiếp tại địa chỉ: `https://slide-to-video-xxx.vercel.app`!

---

## 📄 Bản Quyền & Giấy Phép
Dự án được phát triển phục vụ mục đích nghiên cứu và giáo dục đại học. Giữ toàn quyền sở hữu trí tuệ © 2026 Vũ Minh Kiệt.