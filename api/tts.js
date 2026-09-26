// Vercel Serverless Function: Unified High Quality Vietnamese Speech Engine
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
    const { text } = req.body || {};

    if (!text || text.trim().length === 0) {
      return res.status(400).json({ error: 'Missing text parameter' });
    }

    const cleanText = text.replace(/\[P\d\]/g, '').replace(/\s+/g, ' ').trim();

    // 100% ĐỒNG BỘ: Sử dụng DUY NHẤT 1 loại giọng đọc tiếng Việt chuẩn sư phạm (Google TTS vi)
    const audioBuffer = await fetchGoogleTTSFull(cleanText, 'vi');
    res.setHeader('Content-Type', 'audio/mpeg');
    return res.status(200).send(audioBuffer);

  } catch (error) {
    console.error('[TTS Server Error]:', error);
    return res.status(500).json({ error: error.message || 'Internal Server Error' });
  }
};
