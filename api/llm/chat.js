// Vercel Serverless Function: LLM Proxy (Hỗ trợ chuẩn xác cả OpenAI và Google Gemini Native Multimodal API)
async function callNativeGemini(apiKey, model, messages, maxTokens, temperature, signal) {
  const contents = [];
  let systemInstruction = null;

  for (const m of messages) {
    if (m.role === 'system') {
      const sysText = (typeof m.content === 'string') ? m.content : JSON.stringify(m.content);
      systemInstruction = { parts: [{ text: sysText }] };
      continue;
    }
    const role = (m.role === 'assistant') ? 'model' : 'user';
    const parts = [];
    if (typeof m.content === 'string') {
      parts.push({ text: m.content });
    } else if (Array.isArray(m.content)) {
      for (const item of m.content) {
        if (item.type === 'text' && item.text) {
          parts.push({ text: item.text });
        } else if (item.type === 'image_url' && item.image_url?.url) {
          const u = item.image_url.url;
          if (u.startsWith('data:')) {
            const commaIdx = u.indexOf(',');
            const meta = u.slice(0, commaIdx);
            const b64 = u.slice(commaIdx + 1);
            const mime = meta.split(';')[0].replace('data:', '') || 'image/jpeg';
            parts.push({ inline_data: { mime_type: mime, data: b64 } });
          }
        }
      }
    }
    if (parts.length > 0) {
      contents.push({ role, parts });
    }
  }

  let geminiModel = 'gemini-1.5-flash';
  if (typeof model === 'string' && model.includes('gemini-')) {
    geminiModel = model;
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${geminiModel}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const payload = {
    contents,
    generationConfig: {
      temperature: temperature ?? 0.2,
      maxOutputTokens: maxTokens || 1500
    }
  };
  if (systemInstruction) {
    payload.systemInstruction = systemInstruction;
  }

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal
  });

  if (!res.ok) {
    const errTxt = await res.text();
    throw new Error(`Google Gemini HTTP ${res.status}: ${errTxt.slice(0, 250)}`);
  }

  const data = await res.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
  return {
    choices: [
      {
        message: {
          role: 'assistant',
          content: text
        }
      }
    ]
  };
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const body = (typeof req.body === 'string') ? JSON.parse(req.body) : (req.body || {});
    const customKey = body.apiKey && body.apiKey.trim();
    const requestedModel = body.model;
    const maxTokens = Math.min(body.max_tokens || 1500, 2500);
    const temperature = body.temperature ?? 0.3;
    const messages = body.messages || [];

    // TRƯỜNG HỢP 1: NGƯỜI DÙNG DÙNG KEY RIÊNG
    if (customKey) {
      const isGemini = customKey.startsWith('AIzaSy');
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);

      try {
        if (isGemini) {
          const result = await callNativeGemini(customKey, requestedModel || 'gemini-1.5-flash', messages, maxTokens, temperature, controller.signal);
          clearTimeout(timeoutId);
          return res.status(200).json(result);
        } else {
          // OpenAI hoặc OpenRouter
          let targetUrl = 'https://api.openai.com/v1/chat/completions';
          if (body.baseUrl) {
            targetUrl = `${body.baseUrl.replace(/\/+$/, '')}/chat/completions`;
          }
          const targetModel = requestedModel || 'gpt-4o-mini';

          const reqHeaders = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${customKey}`
          };
          if (body.baseUrl && body.baseUrl.includes('openrouter')) {
            reqHeaders['HTTP-Referer'] = 'https://slide-to-video-sigma.vercel.app/';
            reqHeaders['X-Title'] = 'Slide to Video';
          }

          const upstreamRes = await fetch(targetUrl, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              model: targetModel,
              messages: messages,
              max_tokens: maxTokens,
              temperature: temperature
            }),
            signal: controller.signal
          });
          clearTimeout(timeoutId);

          if (upstreamRes.ok) {
            const data = await upstreamRes.json();
            return res.status(200).json(data);
          }

          const errText = await upstreamRes.text();
          return res.status(upstreamRes.status).json({
            error: `OpenAI phản hồi lỗi HTTP ${upstreamRes.status}`,
            details: errText.slice(0, 300)
          });
        }
      } catch (err) {
        clearTimeout(timeoutId);
        return res.status(500).json({
          error: `Lỗi xử lý AI: ${err.message}`,
          details: err.stack?.slice(0, 200)
        });
      }
    }

    // TRƯỜNG HỢP 2: DÙNG KEY HỆ THỐNG MẶC ĐỊNH
    const envGemini = (process.env.GEMINI_API_KEY || '').trim();
    const envOpenai = (process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY || '').trim();

    const candidates = [];
    if (body.provider === 'openai' || requestedModel?.includes('gpt')) {
      if (envOpenai) candidates.push({ provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: requestedModel || 'gpt-4o-mini' });
      if (envGemini) candidates.push({ provider: 'Gemini', apiKey: envGemini, model: 'gemini-1.5-flash' });
    } else {
      if (envGemini) candidates.push({ provider: 'Gemini', apiKey: envGemini, model: requestedModel || 'gemini-1.5-flash' });
      if (envOpenai) candidates.push({ provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' });
    }

    let lastError = null;
    for (const cand of candidates) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 40000);

        if (cand.provider === 'Gemini') {
          const result = await callNativeGemini(cand.apiKey, cand.model, messages, maxTokens, temperature, controller.signal);
          clearTimeout(timeoutId);
          return res.status(200).json(result);
        } else {
          let candUrl = `${cand.baseUrl.replace(/\/+$/, '')}/chat/completions`;
          const upstreamRes = await fetch(candUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${cand.apiKey}`
            },
            body: JSON.stringify({
              model: cand.model,
              messages: messages,
              max_tokens: maxTokens,
              temperature: temperature
            }),
            signal: controller.signal
          });
          clearTimeout(timeoutId);

          if (upstreamRes.ok) {
            const data = await upstreamRes.json();
            return res.status(200).json(data);
          }
          const errText = await upstreamRes.text();
          lastError = `[${cand.provider}] HTTP ${upstreamRes.status}: ${errText.slice(0, 150)}`;
        }
      } catch (e) {
        lastError = `[${cand.provider}] ${e.message}`;
      }
    }

    return res.status(500).json({
      error: 'Khóa mặc định hệ thống đang bảo trì hoặc chưa cấu hình trên máy chủ.',
      details: lastError || 'Vui lòng dán API Key cá nhân trong Cấu hình AI (⚙️).'
    });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'Lỗi xử lý LLM proxy trên Vercel' });
  }
};
