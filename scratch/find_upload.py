import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

for i, l in enumerate(lines):
    if 'change' in l and 'addEventListener' in l and 'file' in l.lower():
        print(f"{i}: {l.strip()}")
    elif 'upload' in l.lower() and 'input' in l.lower() and 'file' in l.lower():
        print(f"{i}: {l.strip()}")
