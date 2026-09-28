# -*- coding: utf-8 -*-
"""Script test nhanh Hybrid Extractor — chỉ test bước OCR + Layout (không gọi LLM).

Mục đích: Xem text đã parse có đủ chất lượng chưa, ước lượng token tiết kiệm.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import time

# Thêm path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.hybrid_extractor import HybridExtractor, estimate_token_count


def test_pdf(pdf_path: str):
    """Test bóc tách PDF."""
    p = Path(pdf_path)
    if not p.exists():
        print(f"❌ File không tồn tại: {pdf_path}")
        return

    print(f"📄 Đang parse: {p.name}")
    print("=" * 70)

    with open(p, "rb") as f:
        file_bytes = f.read()

    extractor = HybridExtractor()
    t0 = time.time()

    if p.suffix.lower() == ".pdf":
        slides = extractor.extract_from_pdf(file_bytes)
    elif p.suffix.lower() == ".pptx":
        slides = extractor.extract_from_pptx(file_bytes)
    elif p.suffix.lower() == ".docx":
        slides = extractor.extract_from_docx(file_bytes)
    else:
        print(f"❌ Không hỗ trợ: {p.suffix}")
        return

    elapsed = time.time() - t0

    total_input_tokens = 0
    for slide in slides:
        md = slide.to_structured_markdown()
        tokens = estimate_token_count(md)
        total_input_tokens += tokens

        print(f"\n{'─' * 50}")
        print(f"📌 Slide {slide.page_number} | Tiêu đề: {slide.title or '(không có)'}")
        print(f"   Blocks: {len(slide.blocks)} | "
              f"Ảnh: {'✅' if slide.has_images else '❌'} | "
              f"Bảng: {'✅' if slide.has_tables else '❌'} | "
              f"~{tokens} tokens")

        # In nội dung rút gọn
        preview = md[:300].replace("\n", " ↵ ")
        print(f"   Nội dung: {preview}...")

    # Tổng kết
    vlm_tokens = len(slides) * 15000
    import math
    num_requests_batch = math.ceil(len(slides) / 5)
    prompt_overhead = num_requests_batch * 200
    hybrid_total = total_input_tokens + prompt_overhead
    savings = round((1 - hybrid_total / vlm_tokens) * 100, 1) if vlm_tokens > 0 else 0

    print(f"\n{'=' * 70}")
    print(f"📊 TỔNG KẾT")
    print(f"   Tổng slides:     {len(slides)}")
    print(f"   Thời gian parse: {elapsed*1000:.0f}ms")
    print(f"   ─────────────────────────────────────")
    print(f"   VLM thuần:       ~{vlm_tokens:>8,} tokens ({len(slides)} requests)")
    print(f"   Hybrid (batch):  ~{hybrid_total:>8,} tokens ({num_requests_batch} requests)")
    print(f"   ─────────────────────────────────────")
    print(f"   💰 TIẾT KIỆM:   ~{savings}% token | {len(slides) - num_requests_batch} ít requests hơn")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    import glob

    # Tìm file PDF/PPTX trong thư mục data
    test_files = []

    # Tìm trong data/demo
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if data_dir.exists():
        test_files.extend(data_dir.rglob("*.pdf"))
        test_files.extend(data_dir.rglob("*.pptx"))

    # Tìm trong thư mục Tài Liệu
    doc_dir = Path(r"d:\Project\Slide to Video\Tài Liệu")
    if doc_dir.exists():
        test_files.extend(doc_dir.glob("*.pdf"))

    if not test_files:
        print("⚠️  Không tìm thấy file test. Truyền đường dẫn qua dòng lệnh:")
        print("   python test_hybrid.py <path-to-pdf-or-pptx>")
        sys.exit(1)

    # Test file đầu tiên, hoặc file từ argument
    if len(sys.argv) > 1:
        test_pdf(sys.argv[1])
    else:
        print(f"🔍 Tìm thấy {len(test_files)} file test:")
        for i, f in enumerate(test_files[:5]):
            print(f"   [{i+1}] {f.name}")
        print()
        test_pdf(str(test_files[0]))
