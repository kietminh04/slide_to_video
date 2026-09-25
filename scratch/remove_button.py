import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'<button class="mindmap-ctrl-btn" id="btn-rag-ingest"[\s\S]*?</button>'
content = re.sub(pattern, '', content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed btn-rag-ingest")
