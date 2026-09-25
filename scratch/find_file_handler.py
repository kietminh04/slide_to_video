import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

start = -1
end = -1
for i, l in enumerate(lines):
    if 'function handleFiles' in l or 'function processPdfFile' in l or 'function handleFileDrop' in l:
        print(f"Found at {i}: {l.strip()}")
