import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'id="toast"' in l or "id='toast'" in l:
        print(f"{i+1}: {l.strip()}")
