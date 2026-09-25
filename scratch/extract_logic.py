import re
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

out = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\btn_pptx.txt', 'w', encoding='utf-8')
for i, m in enumerate(re.finditer(r'getElementById\(\s*[\'"]btn-export', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+3500)])
out.close()
