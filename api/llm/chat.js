// Vercel Serverless Function: LLM Proxy (Bảo mật API Key & Báo lỗi minh bạch upstream)
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

    // TRƯỜNG HỢP 1: NGƯỜI DÙNG DÙNG KEY RIÊNG (OpenAI hoặc Gemini)
    if (customKey) {
      const isOpenAI = customKey.startsWith('sk-');
      let targetUrl = isOpenAI ? 'https://api.openai.com/v1/chat/completions' : 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions';
      if (body.baseUrl) {
        targetUrl = `${body.baseUrl.replace(/\/+$/, '')}/chat/completions`;
      }
      const targetModel = requestedModel || (isOpenAI ? 'gpt-4o-mini' : 'gemini-2.5-flash');

      const reqHeaders = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${customKey}`
      };
      if (body.baseUrl && body.baseUrl.includes('openrouter')) {
        reqHeaders['HTTP-Referer'] = 'https://slide-to-video-sigma.vercel.app/';
        reqHeaders['X-Title'] = 'Slide to Video';
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s timeout (phù hợp vercel maxDuration: 60s và xử lý Vision AI)

      try {
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

        // Báo lỗi rõ ràng từ chính Upstream của người dùng (OpenAI / Gemini)
        const errText = await upstreamRes.text();
        return res.status(upstreamRes.status).json({
          error: `${isOpenAI ? 'OpenAI' : 'Google Gemini'} phản hồi lỗi HTTP ${upstreamRes.status}`,
          details: errText.slice(0, 300)
        });
      } catch (err) {
        clearTimeout(timeoutId);
        return res.status(504).json({
          error: `Kết nối tới ${isOpenAI ? 'OpenAI' : 'Google Gemini'} bị quá thời gian (Timeout 45s)`,
          details: err.message
        });
      }
    }

    // TRƯỜNG HỢP 2: DÙNG KEY HỆ THỐNG MẶC ĐỊNH
    const envGemini = process.env.GEMINI_API_KEY || '';
    const envOpenai = process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY || '';

    const candidates = [];
    if (body.provider === 'openai' || requestedModel?.includes('gpt')) {
      if (envOpenai) candidates.push({ provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: requestedModel || 'gpt-4o-mini' });
      if (envGemini) candidates.push({ provider: 'Gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash' });
    } else {
      if (envGemini) candidates.push({ provider: 'Gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: requestedModel || 'gemini-2.5-flash' });
      if (envOpenai) candidates.push({ provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' });
    }

    let lastError = null;
    for (const cand of candidates) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 35000);
        const upstreamRes = await fetch(`${cand.baseUrl.replace(/\/+$/, '')}/chat/completions`, {
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
