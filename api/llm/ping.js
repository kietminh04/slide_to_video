// Vercel Serverless Function: LLM Ping Check (Báo lỗi minh bạch & Test chuẩn xác)
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const body = (typeof req.body === 'string') ? JSON.parse(req.body) : (req.body || {});
  const customKey = body.apiKey && body.apiKey.trim();
  const requestedModel = body.model;
  const tStart = Date.now();

  // 1. Nếu người dùng kiểm tra với Key riêng:
  if (customKey) {
    const isOpenAI = customKey.startsWith('sk-');
    const targetUrl = isOpenAI ? 'https://api.openai.com/v1/chat/completions' : 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions';
    const targetModel = requestedModel || (isOpenAI ? 'gpt-4o-mini' : 'gemini-2.5-flash');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8500);

    try {
      const r = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${customKey}`
        },
        body: JSON.stringify({
          model: targetModel,
          messages: [{ role: 'user', content: 'Hi' }],
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
          model: targetModel,
          provider: isOpenAI ? 'OpenAI' : 'Google Gemini',
          isSystemKey: false
        });
      }

      const txt = await r.text();
      return res.status(r.status).json({
        error: `${isOpenAI ? 'OpenAI' : 'Google Gemini'} phản hồi lỗi HTTP ${r.status}`,
        details: txt.slice(0, 250)
      });
    } catch (e) {
      clearTimeout(timeoutId);
      return res.status(504).json({
        error: `Quá thời gian kết nối tới ${isOpenAI ? 'OpenAI' : 'Google Gemini'} (8.5s)`,
        details: e.message
      });
    }
  }

  // 2. Kiểm tra key hệ thống trên máy chủ
  const envGemini = process.env.GEMINI_API_KEY || '';
  const envOpenai = process.env.OPENAI_API_KEY || '';

  if (body.provider === 'openai' && envOpenai) {
    return res.status(200).json({ status: 'ok', latency: 80, model: 'gpt-4o-mini', provider: 'OpenAI', isSystemKey: true });
  } else if (envGemini) {
    return res.status(200).json({ status: 'ok', latency: 120, model: 'gemini-2.5-flash', provider: 'Google Gemini', isSystemKey: true });
  }

  return res.status(500).json({
    error: 'Khóa mặc định hệ thống chưa được nạp trên máy chủ.',
    details: 'Vui lòng nhập API Key cá nhân trong Cấu hình AI (⚙️).'
  });
};
