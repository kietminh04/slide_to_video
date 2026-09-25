// Vercel Serverless Function: High Quality TTS Audio Proxy (OpenAI TTS + Google Neural Fallback)
const https = require('https');

function fetchGoogleTTSChunk(text, lang = 'vi') {
  return new Promise((resolve, reject) => {
    const url = 'https://translate.google.com/translate_tts?ie=UTF-8&q=' + encodeURIComponent(text) + '&tl=' + lang + '&client=tw-ob';
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' } }, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`Google TTS status code: ${res.statusCode}`));
      }
      const chunks = [];
      res.on('data', d => chunks.push(d));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    }).on('error', reject);
  });
}

async function fetchGoogleTTSFull(text, lang = 'vi') {
  // Tách văn bản thành các câu hoặc phân đoạn <= 180 ký tự
  const sentences = text.match(/[^.!?\n,;]+[.!?\n,;]+|[^.!?\n,;]+$/g) || [text];
  const chunks = [];
  let cur = '';
  for (const s of sentences) {
    if ((cur + ' ' + s).length > 180) {
      if (cur) chunks.push(cur.trim());
      cur = s;
    } else {
      cur = cur ? cur + ' ' + s : s;
    }
  }
  if (cur && cur.trim()) chunks.push(cur.trim());

  if (chunks.length === 0) chunks.push(text.slice(0, 180));

  const buffers = [];
  for (const chunk of chunks) {
    if (chunk.trim()) {
      const b = await fetchGoogleTTSChunk(chunk.trim(), lang);
      buffers.push(b);
    }
  }
  return Buffer.concat(buffers);
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
    const { text, voice = 'quynh_anh', model = 'tts-1', apiKey } = req.body || {};

    if (!text || text.trim().length === 0) {
      return res.status(400).json({ error: 'Missing text parameter' });
    }

    const cleanText = text.replace(/\[P\d\]/g, '').replace(/\s+/g, ' ').trim();
    const key = apiKey || process.env.OPENAI_API_KEY;

    // 1. NẾU CÓ OPENAI KEY VÀ CHỌN GIỌNG OPENAI HOẶC USER MUỐN CHẤT LƯỢNG CAO
    const openaiVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
    const isExplicitOpenAIVoice = openaiVoices.includes(voice);

    if (key && (isExplicitOpenAIVoice || voice === 'quynh_anh' || voice === 'mai_phuong')) {
      // Map giọng tiếng Việt sang giọng OpenAI tương ứng
      let chosenVoice = voice;
      if (voice === 'quynh_anh') chosenVoice = 'nova';      // Nữ nhẹ nhàng, rõ ràng
      else if (voice === 'mai_phuong') chosenVoice = 'shimmer'; // Nữ ấm áp, dịu dàng
      else if (voice === 'nam_an') chosenVoice = 'echo';        // Nam trầm ấm
      else if (voice === 'minh_quang') chosenVoice = 'onyx';    // Nam sâu lắng, chuyên nghiệp
      else if (!openaiVoices.includes(chosenVoice)) chosenVoice = 'nova';

      try {
        const openaiRes = await fetch('https://api.openai.com/v1/audio/speech', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${key}`
          },
          body: JSON.stringify({
            model: model || 'tts-1',
            input: cleanText.slice(0, 4000),
            voice: chosenVoice
          })
        });

        if (openaiRes.ok) {
          const audioBuffer = await openaiRes.arrayBuffer();
          res.setHeader('Content-Type', 'audio/mpeg');
          return res.status(200).send(Buffer.from(audioBuffer));
        }
      } catch (err) {
        console.warn('[OpenAI TTS Error, falling back to Google TTS]:', err);
      }
    }

    // 2. GIỌNG NỮ TIẾNG VIỆT CHUẨN TỰ NHIÊN / QUỐC TẾ (GOOGLE TTS ENGINE)
    const isEnglish = (voice === 'jenny_en' || voice === 'guy_en' || voice === 'fable');
    const lang = isEnglish ? 'en' : 'vi';

    const googleMp3Buffer = await fetchGoogleTTSFull(cleanText, lang);
    res.setHeader('Content-Type', 'audio/mpeg');
    return res.status(200).send(googleMp3Buffer);

  } catch (error) {
    console.error('[TTS Server Error]:', error);
    return res.status(500).json({ error: error.message || 'Internal Server Error' });
  }
};
