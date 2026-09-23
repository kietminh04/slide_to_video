// Vercel Serverless Function: LLM Proxy (Bảo mật API Key trên Server)
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
    const envGemini = process.env.GEMINI_API_KEY;
    const envOpenai = process.env.OPENAI_API_KEY;

    let apiKey = body.apiKey || envGemini || envOpenai;
    let provider = body.provider;

    if (!apiKey) {
      return res.status(400).json({
        error: 'Chưa cấu hình API Key trên Vercel. Hãy thêm GEMINI_API_KEY hoặc OPENAI_API_KEY trong mục Settings -> Environment Variables trên Vercel.'
      });
    }

    if (!provider) {
      if (apiKey.startsWith('AIzaSy') || apiKey.startsWith('AIza') || apiKey === envGemini) {
        provider = 'gemini_local';
      } else {
        provider = 'openai';
      }
    }

    let baseUrl = body.baseUrl;
    let model = body.model;

    if (provider === 'gemini_local' || apiKey.startsWith('AIza')) {
      baseUrl = 'https://generativelanguage.googleapis.com/v1beta/openai';
      if (!model || model.startsWith('gpt')) model = 'gemini-2.0-flash';
    } else {
      baseUrl = baseUrl || 'https://api.openai.com/v1';
      if (!model || model.startsWith('gemini')) model = 'gpt-4o-mini';
    }

    const forwardPayload = {
      model: model,
      messages: body.messages || [],
      max_tokens: body.max_tokens || 500,
      temperature: body.temperature || 0.6
    };

    const targetUrl = `${baseUrl.replace(/\/+$/, '')}/chat/completions`;
    const upstreamRes = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify(forwardPayload)
    });

    const data = await upstreamRes.json();
    return res.status(upstreamRes.status).json(data);
  } catch (err) {
    return res.status(500).json({ error: err.message || 'Lỗi xử lý LLM proxy trên Vercel' });
  }
};
