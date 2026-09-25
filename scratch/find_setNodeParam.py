import re
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

out = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\usages_setNodeParam.txt', 'w', encoding='utf-8')
for i, m in enumerate(re.finditer(r'setNodeParam', content)):
    out.write(f'\n--- MATCH {i} ---\n' + content[max(0, m.start()-500):min(len(content), m.start()+500)])
out.close()
