import sys
sys.stdout.reconfigure(encoding='utf-8')
content = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8').read().split('\n')
start = -1
for i, l in enumerate(content):
    if 'async function extractVisualSlideStructure' in l:
        start = i
        break

if start != -1:
    end = min(start + 150, len(content))
    for i in range(start, min(start+300, len(content))):
        if content[i].startswith('    }'):
            end = i
    with open('scratch/extractVisualSlideStructure.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(content[start:end+1]))
    print("Done")
else:
    print("Not found")
