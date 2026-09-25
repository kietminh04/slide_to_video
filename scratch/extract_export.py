import re

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

# Tim nut btn-export-pptx hoac giong giong export
m = re.search(r'document\.getElementById\([\'"]btn-export-pptx[\'"]\)\?\.addEventListener[\s\S]*?(?=document\.getElementById|\Z)', content)
if m:
    with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\export_pptx.txt', 'w', encoding='utf-8') as out:
        out.write(m.group(0))
    print("Found btn-export-pptx")
else:
    print("Not found btn-export-pptx")
