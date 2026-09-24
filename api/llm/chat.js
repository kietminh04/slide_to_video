// Vercel Serverless Function: LLM Proxy (Bảo mật API Key trên Server & Auto-Cascade Fallback)
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
    const envGemini = process.env.GEMINI_API_KEY || 'AQ.Ab8RN6Iiy_lvpeUOc_0fG385dl88DQQWYdtbHsHuIuAaGR6zag';
    const envOpenai = process.env.OPENAI_API_KEY || '';

    const customKey = body.apiKey && body.apiKey.trim();
    const requestedModel = body.model;
    const maxTokens = body.max_tokens || 3500;
    const temperature = body.temperature ?? 0.2;
    const messages = body.messages || [];

    // Danh sách ứng viên tự động chuyển tiếp (Cascade Candidates)
    const candidates = [];

    // Nếu người dùng cung cấp Key riêng:
    if (customKey) {
      if (customKey.startsWith('sk-')) {
        candidates.push({
          provider: 'openai',
          apiKey: customKey,
          baseUrl: 'https://api.openai.com/v1',
          model: requestedModel || 'gpt-4o-mini'
        });
      } else {
        candidates.push({
          provider: 'gemini',
          apiKey: customKey,
          baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
          model: (requestedModel && !requestedModel.includes('gpt')) ? requestedModel : 'gemini-2.5-flash-lite'
        });
      }
    }

    // Các ứng viên mặc định của hệ thống
    const isExplicitOpenAI = (body.provider === 'openai' || requestedModel?.includes('gpt'));
    if (isExplicitOpenAI) {
      if (envOpenai) {
        candidates.push({ provider: 'openai', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: requestedModel || 'gpt-4o-mini' });
      }
      candidates.push(
        { provider: 'gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash-lite' },
        { provider: 'gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash' }
      );
    } else {
      const primaryGemini = (requestedModel && !requestedModel.includes('gpt')) ? requestedModel : 'gemini-2.5-flash';
      candidates.push(
        { provider: 'gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: primaryGemini },
        { provider: 'gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash-lite' }
      );
      if (envOpenai) {
        candidates.push({ provider: 'openai', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' });
      }
    }

    let lastError = null;
    for (const cand of candidates) {
      try {
        const targetUrl = `${cand.baseUrl.replace(/\/+$/, '')}/chat/completions`;
        const payload = {
          model: cand.model,
          messages: messages,
          max_tokens: maxTokens,
          temperature: temperature
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 25000);

        const upstreamRes = await fetch(targetUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${cand.apiKey}`
          },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (upstreamRes.ok) {
          const data = await upstreamRes.json();
          // Kiểm tra xem phản hồi có nội dung không
          const content = data.choices?.[0]?.message?.content;
          if (content && content.trim().length > 0) {
            return res.status(200).json(data);
          }
        }

        const errText = await upstreamRes.text();
        lastError = `[${cand.provider}:${cand.model}] HTTP ${upstreamRes.status}: ${errText.slice(0, 150)}`;
        console.warn(`[Proxy Cascade] Fallback từ ${cand.model} vì lỗi:`, lastError);
      } catch (e) {
        lastError = `[${cand.provider}:${cand.model}] ${e.message}`;
        console.warn(`[Proxy Cascade] Network exception từ ${cand.model}:`, e.message);
      }
    }

    return res.status(500).json({
      error: 'Tất cả các mô hình LLM dự phòng đều phản hồi không thành công.',
      details: lastError
    });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'Lỗi xử lý LLM proxy trên Vercel' });
  }
};
