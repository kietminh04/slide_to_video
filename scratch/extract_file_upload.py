import re

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    content = f.read()

res = re.findall(r'document\.getElementById\([\'"](?:source-file-input|modal-file-input)[\'"]\)\?\.addEventListener\([\'"]change[\'"][\s\S]*?(?=\}\);)', content)
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\file_upload_logic.txt', 'w', encoding='utf-8') as out:
    out.write('\n\n======\n\n'.join(res))
