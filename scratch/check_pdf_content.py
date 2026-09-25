import sys
import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\viole\Downloads\Chuong-5.-Phuong-thuc-tin-dung-CT.pdf'

try:
    doc = fitz.open(pdf_path)
    print(f"Tổng số trang: {doc.page_count}")
    
    # In nội dung text 10 trang đầu
    for i in range(min(15, doc.page_count)):
        page = doc[i]
        text = page.get_text()
        print(f"\n--- TRANG {i+1} ---")
        if text.strip():
            print(text.strip()[:1000]) # In 1000 ký tự đầu của mỗi trang
        else:
            print("[Trang không có text - Có thể là ảnh]")
            
except Exception as e:
    print(f"Lỗi: {e}")
