import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')
start = -1
for i, l in enumerate(lines):
    if 'async function buildChaptersFromPages' in l:
        start = i
        break
if start != -1:
    end = start + 120
    with open('scratch/buildChaptersFromPages2.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(lines[start+45:end]))
    print("Done")
