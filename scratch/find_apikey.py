import sys
sys.stdout.reconfigure(encoding='utf-8')
content = open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', encoding='utf-8').read().split('\n')
for i, l in enumerate(content):
    if 'apiKey' in l or 'ApiKey' in l or 'API_KEY' in l:
        print(f'{i}: {l.strip()}')
        if i > 20000: break
