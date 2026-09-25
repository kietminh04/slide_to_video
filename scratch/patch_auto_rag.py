import re
with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r'(showToast\(\'✨ Đã tái cấu trúc sơ đồ bài giảng thành công!\'\);[\s\S]*?renderMindmap\(\);[\s\S]*?)(} catch \(error\))')
match = pattern.search(content)

if match:
    old_block = match.group(1)
    new_block = old_block + """
        // TỰ ĐỘNG NẠP RAG NGAY KHI PHÂN TÍCH XONG
        setTimeout(() => {
          if (typeof triggerRagIngestion === 'function') triggerRagIngestion();
        }, 1000);
        """
    content = content.replace(old_block, new_block)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched auto-RAG successfully!")
else:
    print("Cannot find refactor finish block")
