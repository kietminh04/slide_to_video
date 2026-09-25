const { neon } = require('@neondatabase/serverless');

function getDb() {
  const conn = process.env.STORAGE_URL || process.env.POSTGRES_URL || process.env.DATABASE_URL;
  if (!conn) return null;
  return neon(conn);
}

module.exports = async function (req, res) {
  // Chỉ cho phép method POST
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

  const apiKey = process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Chưa cấu hình OPENAI_API_KEY' });
  }

  try {
    // 1. (Tùy chọn) Xóa dữ liệu cũ của project này nếu đang update lại slide
    await sql`DELETE FROM document_chunks WHERE project_id = ${projectId}`;

    let processedCount = 0;

    // 2. Quét qua từng đoạn text (chunk)
    for (let chunk of chunks) {
      // Ghép tiêu đề chương và nội dung để nhúng (Embedding) cho chuẩn ngữ cảnh
      const textToEmbed = `Chương: ${chunk.chapter_name || ''} - Phần: ${chunk.section_name || ''}. Nội dung: ${chunk.text}`.trim();
      if (textToEmbed.length < 10) continue; // Bỏ qua đoạn quá ngắn

      // 3. Gọi API OpenAI để nhúng Vector (Biến chữ thành mảng số)
      const embedRes = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: textToEmbed
        })
      });

      const embedData = await embedRes.json();
      if (embedData.error) {
        throw new Error(embedData.error.message);
      }
      
      const embeddingArray = embedData.data[0].embedding;
      // Chuyển mảng JS thành định dạng chuỗi '[0.1, 0.2, ...]' để nhét vào cột Vector của Neon
      const embeddingStr = '[' + embeddingArray.join(',') + ']';
      
      // 4. Lưu vào Database Neon
      await sql`
        INSERT INTO document_chunks (project_id, chapter_name, section_name, chunk_text, embedding)
        VALUES (
          ${projectId}, 
          ${chunk.chapter_name || ''}, 
          ${chunk.section_name || ''}, 
          ${chunk.text}, 
          ${embeddingStr}
        )
      `;
      processedCount++;
    }

    return res.status(200).json({ 
      success: true, 
      message: `Đã Vector hóa và nạp thành công ${processedCount} đoạn vào Neon DB.` 
    });

  } catch (error) {
    console.error('RAG Ingest Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
