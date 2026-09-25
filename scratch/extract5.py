import sys
sys.stdout.reconfigure(encoding='utf-8')
content = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8').read().split('\n')

start = -1
for i, l in enumerate(content):
    if 'const LLMClient = {' in l:
        start = i
        break

if start != -1:
    end = start + 300
    with open('scratch/LLMClient_partial.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(content[start:end]))
    print("Done")
