// Vercel Serverless Function: LLM Ping Check (Bảo mật trên Server & Auto-Cascade Fallback)
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const body = (typeof req.body === 'string') ? JSON.parse(req.body) : (req.body || {});
  const envGemini = process.env.GEMINI_API_KEY || 'AQ.Ab8RN6Iiy_lvpeUOc_0fG385dl88DQQWYdtbHsHuIuAaGR6zag';
  const envOpenai = process.env.OPENAI_API_KEY || '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';

  const customKey = body.apiKey && body.apiKey.trim();
  const requestedModel = body.model;
  const tStart = Date.now();

  const candidates = [];

  // 1. Nếu người dùng nhập API Key riêng
  if (customKey) {
    if (customKey.startsWith('sk-')) {
      candidates.push({
        provider: 'OpenAI',
        apiKey: customKey,
        baseUrl: 'https://api.openai.com/v1',
        model: requestedModel || 'gpt-4o-mini'
      });
    } else {
      candidates.push({
        provider: 'Google Gemini',
        apiKey: customKey,
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
        model: (requestedModel && !requestedModel.includes('gpt')) ? requestedModel : 'gemini-2.5-flash-lite'
      });
    }
  } else {
    // 2. Sử dụng khóa hệ thống trên máy chủ (Tự động chuyển tiếp nếu gặp giới hạn tốc độ 429)
    const isExplicitOpenAI = (body.provider === 'openai' || requestedModel?.includes('gpt'));
    if (isExplicitOpenAI) {
      candidates.push(
        { provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: requestedModel || 'gpt-4o-mini' },
        { provider: 'Google Gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash-lite' }
      );
    } else {
      const primaryGeminiModel = (requestedModel && !requestedModel.includes('gpt')) ? requestedModel : 'gemini-2.5-flash';
      candidates.push(
        { provider: 'Google Gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: primaryGeminiModel },
        { provider: 'Google Gemini', apiKey: envGemini, baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.5-flash-lite' },
        { provider: 'OpenAI', apiKey: envOpenai, baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' }
      );
    }
  }

  let lastError = null;
  for (const cand of candidates) {
    try {
      const targetUrl = `${cand.baseUrl.replace(/\/+$/, '')}/chat/completions`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const r = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cand.apiKey}`
        },
        body: JSON.stringify({
          model: cand.model,
          messages: [{ role: 'user', content: 'Ping' }],
          max_tokens: 5
        }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      const latency = Date.now() - tStart;
      if (r.ok) {
        return res.status(200).json({
          status: 'ok',
          latency,
          model: cand.model,
          provider: cand.provider,
          isSystemKey: !customKey
        });
      }

      const txt = await r.text();
      lastError = `[${cand.provider}:${cand.model}] HTTP ${r.status}: ${txt.slice(0, 150)}`;
      console.warn(`[Ping Cascade] Thử model tiếp theo do lỗi:`, lastError);
    } catch (e) {
      lastError = `[${cand.provider}:${cand.model}] ${e.message}`;
      console.warn(`[Ping Cascade] Ngoại lệ kết nối:`, lastError);
    }
  }

  return res.status(500).json({
    error: 'Không thể kết nối tới các mô hình AI hoặc tạm thời bị giới hạn tốc độ (RPM).',
    details: lastError
  });
};
