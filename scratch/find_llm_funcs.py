import sys
sys.stdout.reconfigure(encoding='utf-8')
content = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8').read().split('\n')
for i, l in enumerate(content):
    if 'async' in l and '({' in l: pass # skip
    elif l.startswith('      async ') or l.startswith('      ') and '(' in l and ')' in l and '{' in l:
        if 'LLMClient =' in l: continue
        if len(l.strip()) > 3 and not l.strip().startswith('//'):
            print(f'{i}: {l.strip()}')
    if i > 20000: break
