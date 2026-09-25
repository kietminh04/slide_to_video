import re

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'addEventListener\([\'"]dblclick[\'"][\s\S]*?(?=\}\);)', content)
if m:
    with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\dblclick.txt', 'w', encoding='utf-8') as out:
        out.write(m.group(0))
    print("Found dblclick")
else:
    print("Not found dblclick")
