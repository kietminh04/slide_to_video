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

  const { projectId, query, history = [] } = req.body;
  if (!projectId || !query) {
    return res.status(400).json({ error: 'Thiếu projectId hoặc query' });
  }

  const sql = getDb();
  if (!sql) {
    return res.status(500).json({ error: 'Chưa cấu hình DATABASE_URL' });
  }

  const apiKey = process.env.OPENAI_API_KEY || process.env.CLSG_OPENAI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Chưa cấu hình OPENAI_API_KEY' });
  }

  try {
    // 1. Nhúng câu hỏi của User thành Vector
    const embedRes = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: query
      })
    });

    const embedData = await embedRes.json();
    if (embedData.error) throw new Error(embedData.error.message);
    
    const queryEmbedding = '[' + embedData.data[0].embedding.join(',') + ']';

    // 2. Truy vấn Vector Database (Lấy 3 đoạn text liên quan nhất)
    // Dùng toán tử <=> để tính Cosine Distance (Càng nhỏ càng giống nhau)
    // Cosine Similarity = 1 - Cosine Distance
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

    // 3. Cơ chế Định tuyến (Distance Threshold) - Từ chối nếu không khớp
    if (!chunks || chunks.length === 0 || chunks[0].similarity < 0.25) {
      return res.status(200).json({ 
        answer: "Xin lỗi, dựa trên dữ liệu hiện tại của bài giảng, tôi không tìm thấy thông tin liên quan để trả lời câu hỏi này. Bạn có thể hỏi rõ hơn hoặc hỏi về chủ đề khác trong bài giảng được không?",
        sources: []
      });
    }

    // 4. Lắp ráp Prompt RAG
    const contextText = chunks.map((c, i) => 
      `[Tài liệu ${i + 1}] Nguồn: ${c.chapter_name} - ${c.section_name}\nNội dung: ${c.chunk_text}`
    ).join('\n\n');

    const systemPrompt = `Bạn là trợ lý AI sư phạm tên là Copilot, được nhúng trong hệ thống thiết kế video bài giảng.
Bạn phải trả lời câu hỏi của người dùng DỰA VÀO ĐÚNG CÁC TÀI LIỆU được cung cấp bên dưới.
Nếu tài liệu không chứa câu trả lời, hãy nói không biết, tuyệt đối KHÔNG ĐƯỢC TỰ BỊA RA.
Khi trả lời, hãy trích dẫn nguồn một cách tự nhiên (vd: "Theo phần [tên phần]").

[TÀI LIỆU BÀI GIẢNG HIỆN TẠI]:
${contextText}`;

    // Format messages for OpenAI
    const messages = [
      { role: 'system', content: systemPrompt },
      ...history, // Lịch sử chat (vài câu gần nhất)
      { role: 'user', content: query }
    ];

    // 5. Gọi LLM sinh câu trả lời
    const chatRes = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: messages,
        temperature: 0.3
      })
    });

    const chatData = await chatRes.json();
    if (chatData.error) throw new Error(chatData.error.message);

    const answer = chatData.choices[0].message.content;

    return res.status(200).json({ 
      answer: answer,
      sources: chunks.map(c => ({
        chapter: c.chapter_name,
        section: c.section_name,
        score: c.similarity
      }))
    });

  } catch (error) {
    console.error('RAG Chat Error:', error);
    return res.status(500).json({ error: error.message });
  }
};
