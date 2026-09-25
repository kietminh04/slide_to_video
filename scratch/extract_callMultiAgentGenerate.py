import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8') as f:
    lines = f.read().split('\n')

start = -1
end = -1
for i, l in enumerate(lines):
    if 'async function callMultiAgentGenerate' in l:
        start = i
        break

if start != -1:
    for i in range(start, len(lines)):
        if lines[i].startswith('    }'):
            end = i
            break
            
    with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\scratch\callMultiAgentGenerate.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(lines[start:end+1]))
    print(f"Extracted from {start} to {end}")
else:
    print("Not found")
