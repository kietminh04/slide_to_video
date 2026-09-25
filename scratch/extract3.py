import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

start = -1
for i, l in enumerate(lines):
    if 'async function extractSlideDeckWithAI' in l:
        start = i
        break
        
if start != -1:
    end = min(start + 150, len(lines))
    for i in range(start, min(start+300, len(lines))):
        if lines[i].startswith('    }') or lines[i].startswith('    async function'):
            end = i
    with open('scratch/extractSlideDeckWithAI.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(lines[start:end+1]))
    print("Done")
else:
    print("Not found")
