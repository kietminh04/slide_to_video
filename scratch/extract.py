import re
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

out = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\export_matches.txt', 'w', encoding='utf-8')

for i, m in enumerate(re.finditer(r'pptx', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH PPTX {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+500)])

for i, m in enumerate(re.finditer(r'export', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH EXPORT {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+500)])
    
for i, m in enumerate(re.finditer(r'download', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH DOWNLOAD {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+500)])

for i, m in enumerate(re.finditer(r'tải về', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH TẢI VỀ {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+500)])

out.close()
