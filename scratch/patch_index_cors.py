import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# We need to replace the direct endpoint fetch with the `/api/llm/chat` proxy fetch
old_logic = """          const endpoint = `${cfg.baseUrl.replace(/\\/+$/, '')}/chat/completions`;
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
          clearTimeout(llmTId);"""

new_logic = """          // Gọi qua proxy /api/llm/chat để tránh lỗi CORS khi gọi trực tiếp OpenAI từ trình duyệt
          const llmPayloadWithConfig = {
            ...llmPayload,
            apiKey: cfg.apiKey,
            baseUrl: cfg.baseUrl,
            provider: cfg.provider
          };

          const endpoint = (window.location.origin.startsWith('http') && !window.location.origin.includes('file:'))
            ? `${window.location.origin}/api/llm/chat`
            : '/api/llm/chat';
            
          const llmCtl = new AbortController();
          const llmTId = setTimeout(() => llmCtl.abort(), 60000);
          res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(llmPayloadWithConfig),
            signal: llmCtl.signal
          });
          clearTimeout(llmTId);"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    print("Fixed CORS proxy in index.html successfully")
else:
    print("Could not find the old logic string in index.html")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
