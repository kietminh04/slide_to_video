const { neon } = require('@neondatabase/serverless');

function getDb() {
  const conn = process.env.STORAGE_URL || process.env.POSTGRES_URL || process.env.DATABASE_URL;
  if (!conn) return null;
  return neon(conn);
}

module.exports = async function (req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { projectId, query } = req.body;
  if (!projectId || !query) {
    return res.status(400).json({ error: 'Thiếu projectId hoặc query' });
  }

  const sql = getDb();
  if (!sql) {
    return res.status(500).json({ error: 'Chưa cấu hình DATABASE_URL' });
  }

  // Ưu tiên số 1: Luôn dùng Gemini Key để băm câu hỏi (768 chiều khớp với vector DB)
  const geminiKey = req.body.geminiApiKey || (req.body.apiKey && !req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.GEMINI_API_KEY;
  const openaiKey = req.body.openaiApiKey || (req.body.apiKey && req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.OPENAI_API_KEY;

  const apiKey = geminiKey || openaiKey;
  if (!apiKey) {
    // Trả về chunks rỗng để frontend tự fallback local
    return res.status(200).json({ chunks: [] });
  }

  // Chỉ dùng OpenAI băm nếu hoàn toàn KHÔNG có Gemini Key
  const isOpenAI = !geminiKey && !!openaiKey;

  try {
    let queryEmbedding;
    if (isOpenAI) {
      const embedRes = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: query,
          dimensions: 768
        })
      });
      const embedData = await embedRes.json();
      if (embedData.error) throw new Error(embedData.error.message || JSON.stringify(embedData.error));
      queryEmbedding = '[' + embedData.data[0].embedding.join(',') + ']';
    } else {
      // 1. Nhúng câu hỏi của User thành Vector (Gemini 768 chiều)
      const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`;
      const embedRes = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'models/text-embedding-004',
          content: { parts: [{ text: query }] }
        })
      });

      const embedData = await embedRes.json();
      if (embedData.error) throw new Error(embedData.error.message);
      
      queryEmbedding = '[' + embedData.embedding.values.join(',') + ']';
    }

    // 2. Truy vấn Vector Database (Lấy 3 đoạn text liên quan nhất bằng Cosine Distance)
    const chunks = await sql`
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

    // Hạ ngưỡng similarity xuống 0.05 để không bỏ sót các câu hỏi ngắn
    if (!chunks || chunks.length === 0 || chunks[0].similarity < 0.05) {
      return res.status(200).json({ chunks: [] });
    }

    // 3. Trả về đúng 3 đoạn text tốt nhất cho Frontend (KHÔNG DÙNG BACKEND ĐỂ CHAT!)
    return res.status(200).json({ 
      chunks: chunks.map(c => ({
        chapter: c.chapter_name,
        section: c.section_name,
        text: c.chunk_text,
        similarity: c.similarity
      }))
    });

  } catch (error) {
    console.error('RAG Search Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
