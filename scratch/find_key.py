import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')
for i, l in enumerate(lines):
    if 'gemini' in l.lower() or 'openai' in l.lower() or 'key' in l.lower():
        print(f'{i}: {l.strip()}')
        if i > 1500: break
