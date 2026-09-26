const { neon } = require('@neondatabase/serverless');

function getDb() {
  const conn = process.env.STORAGE_URL || process.env.POSTGRES_URL || process.env.DATABASE_URL;
  if (!conn) return null;
  return neon(conn);
}

function isGeminiKey(k) {
  return typeof k === 'string' && k.startsWith('AIzaSy') && k.length >= 30;
}

function isOpenAIKey(k) {
  return typeof k === 'string' && k.startsWith('sk-') && k.length >= 20;
}

module.exports = async function (req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { projectId, query } = req.body || {};
  if (!projectId || !query) {
    return res.status(200).json({ chunks: [] });
  }

  const sql = getDb();
  if (!sql) {
    return res.status(200).json({ chunks: [] });
  }

  // Thu thập các key khả dụng
  const rawGemini = req.body.geminiApiKey || (req.body.apiKey && !req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.GEMINI_API_KEY || '';
  const rawOpenai = req.body.openaiApiKey || (req.body.apiKey && req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY || '';

  const geminiKey = isGeminiKey(rawGemini) ? rawGemini : '';
  const openaiKey = isOpenAIKey(rawOpenai) ? rawOpenai : '';

  try {
    let queryEmbedding = null;

    // 1. Thử tạo Vector bằng Google Gemini nếu key hợp lệ
    if (geminiKey) {
      try {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${geminiKey}`;
        const embedRes = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'models/text-embedding-004',
            content: { parts: [{ text: query }] }
          })
        });
        const embedData = await embedRes.json();
        if (embedData.embedding && embedData.embedding.values) {
          queryEmbedding = '[' + embedData.embedding.values.join(',') + ']';
        }
      } catch (gErr) {
        console.warn('[RAG Search] Gemini embedding failed, attempting OpenAI fallback:', gErr.message);
      }
    }

    // 2. Fallback sang OpenAI text-embedding-3-small (768 dimensions) nếu chưa có embedding
    if (!queryEmbedding && openaiKey) {
      try {
        const embedRes = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${openaiKey}`
          },
          body: JSON.stringify({
            model: 'text-embedding-3-small',
            input: query,
            dimensions: 768
          })
        });
        const embedData = await embedRes.json();
        if (embedData.data && embedData.data[0] && embedData.data[0].embedding) {
          queryEmbedding = '[' + embedData.data[0].embedding.join(',') + ']';
        }
      } catch (oErr) {
        console.warn('[RAG Search] OpenAI embedding failed:', oErr.message);
      }
    }

    // Nếu không tạo được embedding (do không có key hoặc cả 2 API đều lỗi), trả về chunks rỗng để frontend fallback local
    if (!queryEmbedding) {
      return res.status(200).json({ chunks: [] });
    }

    // 3. Truy vấn Vector Database (Lấy 3 đoạn text liên quan nhất bằng Cosine Distance)
    let chunks = [];
    try {
      chunks = await sql`
        SELECT 
          chapter_name, 
          section_name, 
          chunk_text,
          1 - (embedding <=> ${queryEmbedding}::vector) AS similarity
        FROM document_chunks
        WHERE project_id = ${projectId}
        ORDER BY embedding <=> ${queryEmbedding}::vector
        LIMIT 3
      `;
    } catch (sqlErr) {
      console.warn('[RAG Search] SQL Vector query error:', sqlErr.message);
      return res.status(200).json({ chunks: [] });
    }

    // Hạ ngưỡng similarity xuống 0.05 để không bỏ sót các câu hỏi ngắn
    if (!chunks || chunks.length === 0 || chunks[0].similarity < 0.05) {
      return res.status(200).json({ chunks: [] });
    }

    // 4. Trả về đúng 3 đoạn text tốt nhất cho Frontend
    return res.status(200).json({ 
      chunks: chunks.map(c => ({
        chapter: c.chapter_name,
        section: c.section_name,
        text: c.chunk_text,
        similarity: c.similarity
      }))
    });

  } catch (error) {
    console.error('[RAG Search Global Error]', error.message);
    // Luôn trả về 200 kèm chunks rỗng để UI không bao giờ bị gián đoạn hay crash
    return res.status(200).json({ chunks: [] });
  }
};
