import re
with open('d:\\Project\\Slide to Video\\Mã Nguồn Sudo\\index.html', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'function\s+buildMindmapData\b.*?return\s+root.*?\n    \}', content, re.DOTALL)
if m:
    with open('scratch\\buildMindmapData.txt', 'w', encoding='utf-8') as out:
        out.write(m.group(0))
    print("Saved to scratch\\buildMindmapData.txt")
else:
    print("Not found")
