import re
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()
out = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\panel_right.txt', 'w', encoding='utf-8')
m = re.search(r'<div[^>]*id=["\']panel-right["\'][^>]*>.*?</div>\s*</div>\s*</div>', content, re.DOTALL)
if m:
    out.write(m.group(0))
else:
    # Just grab anything around "panel-right"
    for x in re.finditer(r'.{0,500}panel-right.{0,2000}', content, re.DOTALL):
        out.write(x.group(0) + '\n\n---\n\n')
out.close()
