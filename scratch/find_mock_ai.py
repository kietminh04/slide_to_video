import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

for i, l in enumerate(lines):
    if 'Phân tích trọng tâm' in l:
        print(f"Line {i+1}: {l.strip()}")
