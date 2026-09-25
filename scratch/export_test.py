import json
import os

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer('api/export', content, flags=re.IGNORECASE)]
print("api/export docx matches:", matches)
if matches:
    print(content[matches[0]-200:matches[0]+200])

print("download in index.html:", "download" in content.lower())
print("export in index.html:", "export" in content.lower())
print("pptx in index.html:", "pptx" in content.lower())

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\studio\server.py', encoding='utf-8') as f:
    server_code = f.read()
print("pptx in server.py:", "pptx" in server_code.lower())
