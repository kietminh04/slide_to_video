import sys
import fitz

pdf_path = r'C:\Users\viole\Downloads\Chuong-5.-Phuong-thuc-tin-dung-CT.pdf'

try:
    doc = fitz.open(pdf_path)
    print("Fonts on page 0:")
    fonts = doc.get_page_fonts(0)
    for f in fonts:
        print(f)
except Exception as e:
    print("Error:", e)
