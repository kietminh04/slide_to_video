import re

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

res = re.findall(r'<input[^>]+type=[\'"]file[\'"][^>]*>', content, re.IGNORECASE)
print(res)
