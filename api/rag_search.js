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

  // Bắt buộc dùng GEMINI_API_KEY để băm câu hỏi (Đảm bảo luôn so sánh 768 chiều với DB)
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Chưa cấu hình GEMINI_API_KEY trên Vercel để băm Vector' });
  }

  try {
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
    
    const queryEmbedding = '[' + embedData.embedding.values.join(',') + ']';

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

    // Nếu không tìm thấy, trả về mảng rỗng để LLM ở Frontend tự ứng biến
    if (!chunks || chunks.length === 0 || chunks[0].similarity < 0.25) {
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
