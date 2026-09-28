"""CLSG Vision Extraction API — Hỗ trợ 2 chế độ: VLM thuần và Hybrid (OCR+LLM).

Endpoints:
  POST /api/extract-visual-slides     — VLM thuần (gửi ảnh, tốn ~15K tokens/slide)
  POST /api/extract-hybrid-slides     — Hybrid (OCR+Layout+LLM text-only, ~800 tokens/slide)
  GET  /api/health                    — Health check
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import concurrent.futures
import math
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI(title="CLSG Hybrid Extraction API")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "modes": ["vlm", "hybrid"]}


# ─────────────────── ENDPOINT 1: VLM THUẦN (Legacy) ───────────────────

@app.post("/api/extract-visual-slides")
async def extract_visual_slides(file: UploadFile = File(...)):
    """Luồng cũ: render ảnh → gửi VLM. Tốn ~15K tokens/slide."""
    from services.slide_extractor import ImageSlideExtractor
    from services.vision_analyzer import VisionAnalyzer

    ext = file.filename.split('.')[-1].lower()
    file_bytes = await file.read()

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
        raise HTTPException(status_code=400, detail="Không tìm thấy slide/ảnh nào")

    vision_analyzer = VisionAnalyzer()
    slide_data_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(vision_analyzer.analyze_slide, img, idx+1): idx
            for idx, img in enumerate(images)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                slide_data_list.append(future.result())
            except Exception as e:
                print(f"Lỗi VLM: {e}")

    slide_data_list.sort(key=lambda x: x.get("slide_number", 0))
    chapters = build_pedagogical_tree(slide_data_list)

    return {
        "success": True,
        "mode": "vlm",
        "total_pages": len(images),
        "chapters": chapters,
        "raw_slides": slide_data_list,
        "token_estimate": f"~{len(images) * 15000:,} tokens (VLM)"
    }


# ─────────────────── ENDPOINT 2: HYBRID (OCR + LLM) ───────────────────

@app.post("/api/extract-hybrid-slides")
async def extract_hybrid_slides(
    file: UploadFile = File(...),
    batch_mode: bool = Query(True, description="Gộp slides thành batch để tiết kiệm requests"),
    batch_size: int = Query(5, description="Số slide mỗi batch (2-10)", ge=2, le=10),
):
    """Luồng mới Hybrid: OCR + Layout Analysis + LLM text-only.

    Tiết kiệm ~90% token so với VLM thuần.
    13 slides: VLM ~200K tokens → Hybrid ~10K-20K tokens
    """
    from services.hybrid_extractor import HybridExtractor, estimate_token_count
    from services.hybrid_analyzer import HybridAnalyzer

    ext = file.filename.split('.')[-1].lower()
    file_bytes = await file.read()
    t0 = time.time()

    # Tầng 1-2: High-Level Parsing (OCR + Layout)
    extractor = HybridExtractor()

    if ext == 'pdf':
        parsed_slides = extractor.extract_from_pdf(file_bytes)
    elif ext == 'pptx':
        parsed_slides = extractor.extract_from_pptx(file_bytes)
    elif ext == 'docx':
        parsed_slides = extractor.extract_from_docx(file_bytes)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng .{ext} chưa hỗ trợ. Hỗ trợ: pdf, pptx, docx"
        )

    if not parsed_slides:
        raise HTTPException(status_code=400, detail="Không tìm thấy nội dung nào")

    # Ước lượng token trước khi gửi LLM
    slides_text = [s.to_structured_markdown() for s in parsed_slides]
    total_input_tokens = sum(estimate_token_count(t) for t in slides_text)
    # System prompt ~200 tokens × số requests
    num_requests = math.ceil(len(slides_text) / batch_size) if batch_mode else len(slides_text)
    prompt_overhead = num_requests * 200
    total_estimated_tokens = total_input_tokens + prompt_overhead

    t_parse = time.time()

    # Tầng 3: LLM Semantic Understanding (TEXT-ONLY, không ảnh!)
    analyzer = HybridAnalyzer()

    if batch_mode:
        slide_data_list = analyzer.analyze_batch(
            slides_text, start_number=1, batch_size=batch_size
        )
    else:
        slide_data_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(analyzer.analyze_slide, text, idx+1): idx
                for idx, text in enumerate(slides_text)
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    slide_data_list.append(future.result())
                except Exception as e:
                    print(f"[Hybrid] Lỗi: {e}")

    slide_data_list.sort(key=lambda x: x.get("slide_number", 0))
    t_llm = time.time()

    # Xây cây sư phạm
    chapters = build_pedagogical_tree(slide_data_list)

    # So sánh với VLM
    vlm_estimated = len(parsed_slides) * 15000
    savings_pct = round((1 - total_estimated_tokens / vlm_estimated) * 100, 1) if vlm_estimated > 0 else 0

    return {
        "success": True,
        "mode": "hybrid",
        "total_pages": len(parsed_slides),
        "chapters": chapters,
        "raw_slides": slide_data_list,
        "performance": {
            "parse_time_ms": round((t_parse - t0) * 1000),
            "llm_time_ms": round((t_llm - t_parse) * 1000),
            "total_time_ms": round((t_llm - t0) * 1000),
            "num_api_requests": num_requests,
            "batch_mode": batch_mode,
            "batch_size": batch_size,
        },
        "token_stats": {
            "input_tokens": total_input_tokens,
            "prompt_overhead": prompt_overhead,
            "total_estimated": total_estimated_tokens,
            "vlm_estimated": vlm_estimated,
            "savings_percent": savings_pct,
            "summary": f"Hybrid: ~{total_estimated_tokens:,} tokens | VLM: ~{vlm_estimated:,} tokens | Tiết kiệm {savings_pct}%"
        }
    }


# ─────────────────── PEDAGOGICAL TREE BUILDER ───────────────────

def build_pedagogical_tree(slides):
    """Chuyển đổi slides thành cấu trúc chương sư phạm: Bridge → Core → Deep → Bridge."""
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
                "summary": combined_text[:300],
                "mechanism": mech,
                "key_point": ", ".join(slide.get("key_concepts", [])),
                "teaching_notes": slide.get("teaching_notes", ""),
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
