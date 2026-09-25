import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

start = -1
for i, l in enumerate(lines):
    if 'id="source-file-input"' in l or "id='source-file-input'" in l:
        start = i
        break

if start != -1:
    for i in range(max(0, start-20), min(start+20, len(lines))):
        print(f"{i}: {lines[i].strip()}")
else:
    print("Not found")
