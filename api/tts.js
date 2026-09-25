// Vercel Serverless Function: TTS Audio Generation Proxy (OpenAI TTS)
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
    const { text, voice = 'nova', model = 'tts-1', apiKey } = req.body || {};

    if (!text || text.trim().length === 0) {
      return res.status(400).json({ error: 'Missing text parameter' });
    }

    const key = apiKey || process.env.OPENAI_API_KEY;
    if (!key) {
      return res.status(400).json({ error: 'Missing OpenAI API Key for TTS' });
    }

    // Map giọng nếu cần (các giọng hợp lệ của OpenAI: alloy, echo, fable, onyx, nova, shimmer)
    const validVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
    const chosenVoice = validVoices.includes(voice) ? voice : 'nova';

    const openaiRes = await fetch('https://api.openai.com/v1/audio/speech', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${key}`
      },
      body: JSON.stringify({
        model: model || 'tts-1',
        input: text.slice(0, 4000),
        voice: chosenVoice
      })
    });

    if (!openaiRes.ok) {
      const errText = await openaiRes.text();
      return res.status(openaiRes.status).json({ error: `OpenAI TTS error: ${errText}` });
    }

    const audioBuffer = await openaiRes.arrayBuffer();
    res.setHeader('Content-Type', 'audio/mpeg');
    return res.status(200).send(Buffer.from(audioBuffer));
  } catch (error) {
    console.error('[TTS Proxy Error]:', error);
    return res.status(500).json({ error: error.message || 'Internal Server Error' });
  }
};
