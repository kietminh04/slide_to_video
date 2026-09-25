import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

out = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\btn_matches.txt', 'w', encoding='utf-8')
for i, m in enumerate(re.finditer(r'btn-export', content, flags=re.IGNORECASE)):
    out.write(f'\n--- MATCH {i} ---\n' + content[max(0, m.start()-1000):min(len(content), m.start()+3500)])
out.close()
