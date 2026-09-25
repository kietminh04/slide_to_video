from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import concurrent.futures
from services.slide_extractor import ImageSlideExtractor
from services.vision_analyzer import VisionAnalyzer
import uvicorn
import math

app = FastAPI(title="CLSG Vision Extraction API")

# Cấu hình CORS để frontend gọi được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vision_analyzer = VisionAnalyzer()

@app.post("/api/extract-visual-slides")
async def extract_visual_slides(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1].lower()
    file_bytes = await file.read()
    
    # Bước 1: Trích xuất ảnh
    images = []
    if ext == 'pdf':
        images = ImageSlideExtractor.extract_from_pdf(file_bytes)
    elif ext == 'pptx':
        images = ImageSlideExtractor.extract_from_pptx(file_bytes)
    elif ext == 'docx':
        images = ImageSlideExtractor.extract_from_docx(file_bytes)
    else:
        raise HTTPException(status_code=400, detail="Định dạng file không hỗ trợ")

    if not images:
        raise HTTPException(status_code=400, detail="Không tìm thấy slide/ảnh nào trong file")

    # Bước 2: Quét nội dung đa phương thức song song
    slide_data_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(vision_analyzer.analyze_slide, img, idx+1): idx for idx, img in enumerate(images)}
        for future in concurrent.futures.as_completed(futures):
            try:
                slide_data = future.result()
                slide_data_list.append(slide_data)
            except Exception as e:
                print(f"Lỗi future: {e}")

    # Sắp xếp lại theo đúng thứ tự slide_number
    slide_data_list.sort(key=lambda x: x.get("slide_number", 0))

    # Bước 3: Dựng cây sư phạm (Chương -> Phần -> Phân đoạn)
    # Tương thích với cấu trúc của CLSG Studio
    chapters = build_pedagogical_tree(slide_data_list)

    return {
        "success": True,
        "total_pages": len(images),
        "chapters": chapters,
        "raw_slides": slide_data_list
    }

def build_pedagogical_tree(slides):
    """
    Chuyển đổi danh sách slides thành cấu trúc chương sư phạm: Bridge -> Core -> Deep -> Bridge
    """
    chapters = []
    total_slides = len(slides)
    if total_slides == 0:
        return chapters

    num_chapters = 5
    if total_slides <= 6: num_chapters = max(1, total_slides)
    elif total_slides <= 14: num_chapters = 3
    elif total_slides <= 28: num_chapters = 4
    elif total_slides <= 50: num_chapters = 5
    else: num_chapters = min(8, math.ceil(total_slides / 10))

    group_size = max(1, math.ceil(total_slides / num_chapters))

    for ch_idx in range(num_chapters):
        start_idx = ch_idx * group_size
        end_idx = min(total_slides, (ch_idx + 1) * group_size)
        if start_idx >= total_slides:
            break
            
        group_slides = slides[start_idx:end_idx]
        
        # Xác định tiêu đề chương từ slide đầu tiên của group
        ch_title = group_slides[0].get("title", f"Phân đoạn {ch_idx+1}")
        if not ch_title or ch_title.strip() == "":
            ch_title = f"Chương {ch_idx+1}: Nội dung từ Slide {start_idx+1}"

        depth = "core"
        if ch_idx == 0 or ch_idx == num_chapters - 1:
            depth = "bridge"

        items = []
        for it_idx, slide in enumerate(group_slides):
            text_lines = slide.get("text_content", [])
            formulas = slide.get("math_formulas", [])
            desc = slide.get("visual_description", "")
            
            combined_text = " ".join(text_lines)
            if desc:
                combined_text += f" [Mô tả hình: {desc}]"
                
            mech = " ".join(formulas)
            if not mech and desc:
                mech = desc

            items.append({
                "code": f"{ch_idx+1}.1.{it_idx+1}",
                "text": slide.get("title", f"Nội dung slide {slide.get('slide_number')}"),
                "duration": 30,
                "pdfStart": slide.get("slide_number"),
                "pdfEnd": slide.get("slide_number"),
                "pageRange": f"Slide {slide.get('slide_number')}",
                "summary": combined_text[:300], # Lấy 300 ký tự đầu làm summary
                "mechanism": mech,
                "key_point": ", ".join(slide.get("key_concepts", [])),
                "narration": "",
                "visual_type": "split_screen" if (it_idx % 2 == 0) else "process_visualization"
            })

        chapters.append({
            "chapter": f"CHƯƠNG {ch_idx+1}",
            "title": ch_title,
            "depth": depth,
            "visual_type": "split_screen" if ch_idx % 2 == 0 else "process_visualization",
            "sections": [{
                "code": f"{ch_idx+1}.1",
                "title": ch_title,
                "items": items
            }]
        })

    return chapters

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
