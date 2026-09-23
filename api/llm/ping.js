// Vercel Serverless Function: LLM Ping Check
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const envGemini = process.env.GEMINI_API_KEY || 'AQ.Ab8RN6Iiy_lvpeUOc_0fG385dl88DQQWYdtbHsHuIuAaGR6zag';
  const envOpenai = process.env.OPENAI_API_KEY;
  const hasKey = Boolean(envGemini || envOpenai);

  return res.status(200).json({
    status: 'ok',
    hasServerKey: hasKey,
    provider: envGemini ? 'Google Gemini (Vercel Serverless)' : (envOpenai ? 'OpenAI (Vercel Serverless)' : 'none')
  });
};
