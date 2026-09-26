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

  // Ưu tiên số 1: Luôn dùng Gemini Key để băm (tiết kiệm token & chi phí)
  const geminiKey = req.body.geminiApiKey || (req.body.apiKey && !req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.GEMINI_API_KEY;
  const openaiKey = req.body.openaiApiKey || (req.body.apiKey && req.body.apiKey.startsWith('sk-') ? req.body.apiKey : '') || process.env.OPENAI_API_KEY;

  const apiKey = geminiKey || openaiKey;
  if (!apiKey) {
    return res.status(500).json({ error: 'Chưa cấu hình API Key (Vui lòng nhập Key trong Cấu hình AI ⚙️ hoặc cài biến trên Vercel)' });
  }

  // Chỉ dùng OpenAI băm nếu hoàn toàn KHÔNG có Gemini Key
  const isOpenAI = !geminiKey && !!openaiKey;

  try {
    // 0. Tạo bảng & Đảm bảo cột vector là 768 chiều
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
    
    try {
      await sql`ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)`;
    } catch(e) {
      // Nếu có xung đột kiểu dữ liệu cũ, truncate bảng rồi alter
      await sql`TRUNCATE TABLE document_chunks`;
      await sql`ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)`;
    }

    // 1. Xóa dữ liệu cũ của project này nếu đang update lại slide
    await sql`DELETE FROM document_chunks WHERE project_id = ${projectId}`;

    // Chuẩn bị danh sách chunk hợp lệ
    const validChunks = [];
    for (const chunk of chunks) {
      const textToEmbed = `Chương: ${chunk.chapter_name || ''} - Phần: ${chunk.section_name || ''}. Nội dung: ${chunk.text}`.trim();
      if (textToEmbed.length >= 10) {
        validChunks.push({
          chapter_name: chunk.chapter_name || '',
          section_name: chunk.section_name || '',
          textToEmbed
        });
      }
    }

    if (validChunks.length === 0) {
      return res.status(200).json({ success: true, processed: 0, message: 'Không có đoạn văn bản nào đủ dài để nạp' });
    }

    let processedCount = 0;

    if (isOpenAI) {
      // Dùng OpenAI text-embedding-3-small (cố định 768 chiều)
      const batchSize = 50;
      for (let i = 0; i < validChunks.length; i += batchSize) {
        const batch = validChunks.slice(i, i + batchSize);
        const embedRes = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
          },
          body: JSON.stringify({
            model: 'text-embedding-3-small',
            input: batch.map(b => b.textToEmbed),
            dimensions: 768
          })
        });

        const embedData = await embedRes.json();
        if (embedData.error) throw new Error(embedData.error.message || JSON.stringify(embedData.error));

        for (let j = 0; j < batch.length; j++) {
          const embValues = embedData.data[j]?.embedding;
          if (embValues) {
            const embStr = '[' + embValues.join(',') + ']';
            await sql`
              INSERT INTO document_chunks (project_id, chapter_name, section_name, chunk_text, embedding)
              VALUES (${projectId}, ${batch[j].chapter_name}, ${batch[j].section_name}, ${batch[j].textToEmbed}, ${embStr})
            `;
            processedCount++;
          }
        }
      }
    } else {
      // Dùng Google Gemini text-embedding-004 (768 chiều mặc định) với Batch Embed siêu tốc
      const batchSize = 25;
      for (let i = 0; i < validChunks.length; i += batchSize) {
        const batch = validChunks.slice(i, i + batchSize);
        try {
          const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key=${apiKey}`;
          const embedRes = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              requests: batch.map(b => ({
                model: 'models/text-embedding-004',
                content: { parts: [{ text: b.textToEmbed }] }
              }))
            })
          });

          const embedData = await embedRes.json();
          if (embedData.error) throw new Error(embedData.error.message || JSON.stringify(embedData.error));

          if (embedData.embeddings && Array.isArray(embedData.embeddings)) {
            for (let j = 0; j < batch.length; j++) {
              const embValues = embedData.embeddings[j]?.values;
              if (embValues) {
                const embStr = '[' + embValues.join(',') + ']';
                await sql`
                  INSERT INTO document_chunks (project_id, chapter_name, section_name, chunk_text, embedding)
                  VALUES (${projectId}, ${batch[j].chapter_name}, ${batch[j].section_name}, ${batch[j].textToEmbed}, ${embStr})
                `;
                processedCount++;
              }
            }
            continue;
          }
        } catch (batchErr) {
          console.warn('Batch embed error, falling back to sequential embedContent:', batchErr.message);
        }

        // Fallback tuần tự nếu batch gặp lỗi
        for (const item of batch) {
          const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`;
          const embedRes = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model: 'models/text-embedding-004',
              content: { parts: [{ text: item.textToEmbed }] }
            })
          });
          const embedData = await embedRes.json();
          if (embedData.error) throw new Error(embedData.error.message);
          const embStr = '[' + embedData.embedding.values.join(',') + ']';
          await sql`
            INSERT INTO document_chunks (project_id, chapter_name, section_name, chunk_text, embedding)
            VALUES (${projectId}, ${item.chapter_name}, ${item.section_name}, ${item.textToEmbed}, ${embStr})
          `;
          processedCount++;
        }
      }
    }

    return res.status(200).json({ 
      success: true, 
      processed: processedCount,
      message: `Đã Vector hóa và nạp thành công ${processedCount} đoạn (768 chiều) vào Neon DB.` 
    });

  } catch (error) {
    console.error('RAG Ingest Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
