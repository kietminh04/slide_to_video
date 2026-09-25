import sys
import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\viole\Downloads\Chuong-5.-Phuong-thuc-tin-dung-CT.pdf'

try:
    doc = fitz.open(pdf_path)
    print(f"Tổng số trang: {doc.page_count}")
    print(f"Is Encrypted: {doc.is_encrypted}")
    print(f"Metadata: {doc.metadata}")
except Exception as e:
    print(f"Lỗi: {e}")
