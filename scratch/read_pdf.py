import sys
import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'D:\Code\Courses\Vin AI\Courses\Khoá 4\Slide\Phase 1\8. Data ai-assisted and Active Learning.pdf'

try:
    doc = fitz.open(pdf_path)
    print(f"Tổng số trang: {doc.page_count}")
    
    # In nội dung text 10 trang đầu
    for i in range(min(10, doc.page_count)):
        page = doc[i]
        text = page.get_text()
        print(f"\n--- TRANG {i+1} ---")
        if text.strip():
            print(text.strip()[:500]) # In 500 ký tự đầu của mỗi trang
        else:
            print("[Trang không có text - Có thể là ảnh]")
            
except Exception as e:
    print(f"Lỗi: {e}")
