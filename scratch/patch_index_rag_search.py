import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the fetching from rag_chat with rag_search and LLMClient fallback
old_logic = """        try {
          const serverUrl = (window.location.origin.startsWith('http') && !window.location.origin.includes('file:'))
            ? `${window.location.origin}/api/rag_chat`
            : '/api/rag_chat';
          const ctl = new AbortController();
          const tId = setTimeout(() => ctl.abort(), 55000);
          res = await fetch(serverUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: ctl.signal
          });
          clearTimeout(tId);
        } catch (e) {
          console.warn("[Copilot] Lỗi gọi Backend RAG:", e);
        }

        if (res && res.ok) {
          const data = await res.json();
          // Hỗ trợ cả định dạng OpenAI chuẩn (choices) và định dạng RAG Backend trả về (answer)
          let reply = data.answer || (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || '';"""

new_logic = """        try {
          const searchUrl = (window.location.origin.startsWith('http') && !window.location.origin.includes('file:'))
            ? `${window.location.origin}/api/rag_search`
            : '/api/rag_search';
          const searchCtl = new AbortController();
          const searchTId = setTimeout(() => searchCtl.abort(), 15000);
          const searchRes = await fetch(searchUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: searchCtl.signal
          });
          clearTimeout(searchTId);

          let contextText = "Không tìm thấy kiến thức liên quan trong CSDL.";
          if (searchRes && searchRes.ok) {
             const searchData = await searchRes.json();
             if (searchData.chunks && searchData.chunks.length > 0) {
                 contextText = searchData.chunks.map((c, i) => 
                   `[Tài liệu ${i + 1}] Nguồn: ${c.chapter} - ${c.section}\\nNội dung: ${c.text}`
                 ).join('\\n\\n');
             }
          }

          const systemPrompt = `Bạn là SIÊU TRỢ LÝ AI & TRỢ GIẢNG ĐA NĂNG CỦA HỆ THỐNG CLSG STUDIO (HUST AI COPILOT).
Người dùng là giảng viên hoặc học viên. Bạn phải thân thiện, thông thái: đọc hộ, giải thích hộ kiến thức và TRỰC TIẾP ĐIỀU KHIỂN GIAO DIỆN HỘ người dùng.

[KIẾN THỨC BÀI GIẢNG ĐƯỢC RÚT TRÍCH TỪ DATABASE (RAG)]:
${contextText}

[CẤU TRÚC SƠ ĐỒ HIỆN TẠI ĐỂ ĐIỀU KHIỂN GIAO DIỆN]:
${treeSkeleton}

DANH MỤC CÁC LỆNH ĐIỀU KHIỂN GIAO DIỆN BẠN CÓ THỂ RA LỆNH:
1. "keep_only_target": {"type": "keep_only_target", "chapter": 1, "section": "d", "item": "a1"} -> Giữ duy nhất mục này.
2. "keep_chapters_and_sections": {"type": "keep_chapters_and_sections", "chapters": [4], "targetChapter": 1, "sections": ["a", "b"]}
3. "set_only_chapters": {"type": "set_only_chapters", "chapters": [2, 3]}
4. "exclude_chapters": {"type": "exclude_chapters", "chapters": [1]}
5. "include_chapters": {"type": "include_chapters", "chapters": [1]}
6. "focus_chapter": {"type": "focus_chapter", "chapter": 1}
7. "open_editor": {"type": "open_editor", "chapter": 1}
8. "set_total_minutes": {"type": "set_total_minutes", "minutes": 10}
9. "set_chapter_duration": {"type": "set_chapter_duration", "chapter": 1, "seconds": 180}
10. "switch_tab": {"type": "switch_tab", "tab": "mindmap" | "script" | "video"}
11. "speak_narration": {"type": "speak_narration", "text": "Lời thoại..."}
12. "exclude_codes": {"type": "exclude_codes", "codes": ["1.1"]}
13. "include_codes": {"type": "include_codes", "codes": ["1.1"]}
14. "set_only_codes": {"type": "set_only_codes", "codes": ["1.1"]}
15. "focus_code": {"type": "focus_code", "code": "1.1"}
16. "speak_code": {"type": "speak_code", "code": "1.1"}
17. "set_node_config": {"type": "set_node_config", "code": "1.1", "voice": "Nam_MienNam", "speed": 1.25, "locked": true}
18. "set_narration": {"type": "set_narration", "code": "1.1", "narration": "Kịch bản mới..."}
19. "request_illustration": {"type": "request_illustration", "code": "1.1", "prompt": "mô tả hình ảnh"}

QUY TẮC:
1. NẾU NGƯỜI DÙNG HỎI KIẾN THỨC: Phải trả lời DỰA VÀO KIẾN THỨC ĐƯỢC RÚT TRÍCH ở trên. Nếu không tìm thấy, hãy nói là không tìm thấy. TUYỆT ĐỐI KHÔNG SINH RA JSON NẾU KHÔNG YÊU CẦU ĐIỀU KHIỂN UI!
2. NẾU NGƯỜI DÙNG YÊU CẦU ĐIỀU KHIỂN UI ("ẩn", "hiện", "chỉ giữ", "viết kịch bản"): Kèm khối \`\`\`json chứa cấu trúc {"actions": [...]} ở cuối câu trả lời.`;

          const llmPayload = {
            model: cfg.model || 'gemini-2.5-flash',
            messages: [
              { role: 'system', content: systemPrompt },
              ...rollingHistory,
              { role: 'user', content: msg }
            ],
            max_tokens: 2500,
            temperature: 0.3
          };

          const endpoint = `${cfg.baseUrl.replace(/\\/+$/, '')}/chat/completions`;
          const headers = { 'Content-Type': 'application/json' };
          if (cfg.apiKey) {
             headers['Authorization'] = `Bearer ${cfg.apiKey}`;
          }

          const llmCtl = new AbortController();
          const llmTId = setTimeout(() => llmCtl.abort(), 60000);
          res = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(llmPayload),
            signal: llmCtl.signal
          });
          clearTimeout(llmTId);

        } catch (e) {
          console.warn("[Copilot] Lỗi gọi Backend RAG / LLM:", e);
        }

        if (res && res.ok) {
          const data = await res.json();
          let reply = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || '';"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    print("Replaced RAG logic in index.html successfully")
else:
    print("Could not find the old logic string in index.html")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
