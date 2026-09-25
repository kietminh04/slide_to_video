import re
with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r'(<button class="mindmap-ctrl-btn" id="btn-ai-refactor-mindmap"[\s\S]*?</span> Tái Cấu Trúc Sơ Đồ\s*</button>)')
match = pattern.search(content)

if match:
    old_btn = match.group(1)
    new_btn = old_btn + """
            <button class="mindmap-ctrl-btn" id="btn-rag-ingest"
              style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.4), rgba(5, 150, 105, 0.4)); border: 1px solid rgba(16, 185, 129, 0.7); color: #fff; font-weight: 700; padding: 0 14px; gap: 6px; display: flex; align-items: center; margin-left: 8px;"
              title="Nạp kiến thức sơ đồ vào Cơ sở dữ liệu Vector để Chatbot hỏi đáp chuẩn xác">
              <span>📚</span> Nạp Tri Thức RAG
            </button>"""
    content = content.replace(old_btn, new_btn)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched button successfully!")
else:
    print("Still cannot find button")
