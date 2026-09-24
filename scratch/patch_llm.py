import os
import re

files_to_patch = [
    'd:/Project/Slide to Video/Mã Nguồn Sudo/index.html',
    'd:/Project/Slide to Video/Mã Nguồn Sudo/studio/index.html'
]

robust_fetch = """        let res = null;
        try {
          const serverUrl = (window.location.origin.startsWith('http') && !window.location.origin.includes('file:'))
            ? `${window.location.origin}/api/llm/chat`
            : 'https://slide-to-video-sigma.vercel.app/api/llm/chat';
          const proxyPayload = { ...payload, apiKey: cfg.apiKey || '', baseUrl: cfg.baseUrl || '', provider: cfg.provider || 'openai' };
          const ctl = new AbortController();
          const tId = setTimeout(() => ctl.abort(), 8000);
          res = await fetch(serverUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(proxyPayload),
            signal: ctl.signal
          });
          clearTimeout(tId);
        } catch (e) {
          console.warn("[LLM] Server proxy error:", e);
        }

        if ((!res || !res.ok) && cfg.apiKey) {
          try {
            const endpoint = `${cfg.baseUrl.replace(/\\/+$/, '')}/chat/completions`;
            const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${cfg.apiKey}` };
            const ctl = new AbortController();
            const tId = setTimeout(() => ctl.abort(), 8000);
            res = await fetch(endpoint, {
              method: 'POST',
              headers,
              body: JSON.stringify(payload),
              signal: ctl.signal
            });
            clearTimeout(tId);
          } catch (e) {
            console.warn("[LLM] Direct endpoint error:", e);
          }
        }
        if (res && res.ok) {"""

for filepath in files_to_patch:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix btnSaveAiCfg event listener missing setTimeout
    content = re.sub(
        r"(btnSaveAiCfg\.innerHTML = '<span>⏳</span> Đang lưu...';\s*btnSaveAiCfg\.disabled = true;\s*)(const provider = radioProvGemini)",
        r"\1setTimeout(() => {\n      \2",
        content
    )
    
    content = re.sub(
        r"(showToast\(`🎉 Đã lưu cấu hình AI thành công.*?\);\s*)(\}\);)",
        r"\1}, 400);\n    \2",
        content
    )

    # 2. Fix the fetch logic in LLMClient functions
    # Pattern to match:
    # try {
    #   const serverUrl = ...
    #   const res = await fetch(serverUrl, { ... });
    #   if (res.ok) {
    # It might have small variations, but they generally follow this structure.
    
    pattern = re.compile(
        r"try \{\s*const serverUrl = [^;]+;\s*const res = await fetch\(serverUrl, \{\s*method: 'POST',\s*headers: \{ 'Content-Type': 'application/json' \},\s*body: JSON\.stringify\(payload\)\s*\}\);\s*if \(res\.ok\) \{",
        re.DOTALL
    )
    
    content = pattern.sub(robust_fetch, content)

    # 3. Add robust fetch to ping as well? (ping doesn't use messages, so payload is different)
    # Ping already checks cfg.apiKey in some way? No, let's just leave ping as is unless it's an issue.

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done patching.")
