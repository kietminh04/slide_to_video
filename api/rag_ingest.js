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

  const { projectId, chunks } = req.body;
  if (!projectId || !chunks || !Array.isArray(chunks)) {
    return res.status(400).json({ error: 'Thiếu projectId hoặc mảng chunks' });
  }

  const sql = getDb();
  if (!sql) {
    return res.status(500).json({ error: 'Chưa cấu hình DATABASE_URL trên Vercel' });
  }

  // Chú ý: Bắt buộc dùng GEMINI_API_KEY trên Vercel để băm Vector (Tiết kiệm Token & Cố định 768 chiều)
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Chưa cấu hình biến môi trường GEMINI_API_KEY trên Vercel' });
  }

  try {
    // 0. Tạo bảng & Đảm bảo cột vector là 768 chiều (Dành riêng cho Gemini)
    await sql`CREATE EXTENSION IF NOT EXISTS vector`;
    await sql`
      CREATE TABLE IF NOT EXISTS document_chunks (
        id SERIAL PRIMARY KEY,
        project_id TEXT,
        chapter_name TEXT,
        section_name TEXT,
        chunk_text TEXT,
        embedding vector(768)
      )
    `;
    
    // Nếu bảng cũ đang là 1536 chiều, ALTER sẽ báo lỗi. Xóa hết data cũ rồi ALTER lại.
    try {
      await sql`ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)`;
    } catch(e) {
      // Nếu có lỗi do không khớp số chiều data cũ, truncate bảng rồi alter
      await sql`TRUNCATE TABLE document_chunks`;
      await sql`ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)`;
    }

    // 1. Xóa dữ liệu cũ của project này nếu đang update lại slide
    await sql`DELETE FROM document_chunks WHERE project_id = ${projectId}`;

    let processedCount = 0;

    // 2. Quét qua từng đoạn text (chunk)
    for (let chunk of chunks) {
      const textToEmbed = `Chương: ${chunk.chapter_name || ''} - Phần: ${chunk.section_name || ''}. Nội dung: ${chunk.text}`.trim();
      if (textToEmbed.length < 10) continue;

      // 3. Gọi API Gemini để nhúng Vector (768 chiều)
      const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`;
      const embedRes = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'models/text-embedding-004',
          content: { parts: [{ text: textToEmbed }] }
        })
      });

      const embedData = await embedRes.json();
      if (embedData.error) {
        throw new Error(embedData.error.message);
      }
      
      const embeddingArray = embedData.embedding.values;
      const embeddingStr = '[' + embeddingArray.join(',') + ']';
      
      // 4. Lưu vào Database Neon
      await sql`
        INSERT INTO document_chunks (project_id, chapter_name, section_name, chunk_text, embedding)
        VALUES (
          ${projectId}, 
          ${chunk.chapter_name || ''}, 
          ${chunk.section_name || ''}, 
          ${textToEmbed}, 
          ${embeddingStr}
        )
      `;
      processedCount++;
    }

    return res.status(200).json({ 
      success: true, 
      message: `Đã Vector hóa bằng Gemini và nạp thành công ${processedCount} đoạn (768 chiều) vào Neon DB.` 
    });

  } catch (error) {
    console.error('RAG Ingest Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
