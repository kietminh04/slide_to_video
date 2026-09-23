// Vercel Serverless Function: LLM Ping Check (Bảo mật trên Server)
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const body = (typeof req.body === 'string') ? JSON.parse(req.body) : (req.body || {});
  const envGemini = process.env.GEMINI_API_KEY || 'AQ.Ab8RN6Iiy_lvpeUOc_0fG385dl88DQQWYdtbHsHuIuAaGR6zag';
  const envOpenai = process.env.OPENAI_API_KEY;
  const apiKey = body.apiKey || envGemini || envOpenai;

  if (!apiKey) {
    return res.status(400).json({ error: 'Chưa có API key trên server hoặc client.' });
  }

  const tStart = Date.now();
  try {
    const isGemini = (apiKey.startsWith('AQ.') || apiKey.startsWith('AIza') || body.provider === 'gemini_local');
    if (isGemini) {
      const url = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions';
      const r = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: body.model || 'gemini-2.5-flash',
          messages: [{ role: 'user', content: 'Ping' }],
          max_tokens: 2
        })
      });
      const latency = Date.now() - tStart;
      if (!r.ok) {
        const txt = await r.text();
        return res.status(r.status).json({ error: `Gemini API lỗi (${r.status}): ${txt.slice(0, 120)}` });
      }
      return res.status(200).json({
        status: 'ok',
        latency,
        isSystemKey: !body.apiKey,
        provider: 'Google Gemini'
      });
    } else {
      const url = 'https://api.openai.com/v1/chat/completions';
      const r = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: body.model || 'gpt-4o-mini',
          messages: [{ role: 'user', content: 'Ping' }],
          max_tokens: 2
        })
      });
      const latency = Date.now() - tStart;
      if (!r.ok) {
        const txt = await r.text();
        return res.status(r.status).json({ error: `OpenAI API lỗi (${r.status}): ${txt.slice(0, 120)}` });
      }
      return res.status(200).json({
        status: 'ok',
        latency,
        isSystemKey: !body.apiKey,
        provider: 'OpenAI'
      });
    }
  } catch (err) {
    return res.status(500).json({ error: err.message || 'Lỗi kiểm tra kết nối' });
  }
};
