import re

with open("api/rag_chat.js", "r", encoding="utf-8") as f:
    content = f.read()

old_list = '16. "speak_code": {"type": "speak_code", "code": "1.1"}'

new_list = old_list + """
17. "set_node_config": {"type": "set_node_config", "code": "1.1", "voice": "Nam_MienNam", "speed": 1.25, "locked": true} -> Cài đặt giọng đọc, tốc độ, khóa cho mục.
18. "set_narration": {"type": "set_narration", "code": "1.1", "narration": "Kịch bản mới..."} -> Viết lại kịch bản lời thoại của mục.
19. "request_illustration": {"type": "request_illustration", "code": "1.1", "prompt": "mô tả hình ảnh"} -> Yêu cầu ảnh minh họa cho mục."""

if old_list in content:
    content = content.replace(old_list, new_list)
    with open("api/rag_chat.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched api/rag_chat.js")
else:
    print("Could not find prompt in rag_chat.js")
