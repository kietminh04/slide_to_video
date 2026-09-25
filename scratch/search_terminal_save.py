import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('d:\\Project\\Slide to Video\\Mã Nguồn Sudo\\index.html', encoding='utf-8') as f:
    content = f.read()

m2 = re.search(r'document\.getElementById\([\'"]btn-save-terminal[\'"]\).*?\}\);', content, re.DOTALL)
if m2:
    print(m2.group(0))
else:
    print("Not found")
