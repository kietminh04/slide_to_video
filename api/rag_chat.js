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

    const treeSkeleton = req.body.treeSkeleton || "";
    const systemPrompt = `Bạn là SIÊU TRỢ LÝ AI & TRỢ GIẢNG ĐA NĂNG CỦA HỆ THỐNG CLSG STUDIO (HUST AI COPILOT).
Người dùng là giảng viên hoặc học viên. Bạn phải thân thiện, thông thái: đọc hộ, giải thích hộ kiến thức và TRỰC TIẾP ĐIỀU KHIỂN GIAO DIỆN HỘ người dùng.

[KIẾN THỨC BÀI GIẢNG ĐƯỢC RÚT TRÍCH TỪ DATABASE (RAG)]:
${contextText}

[CẤU TRÚC SƠ ĐỒ HIỆN TẠI ĐỂ ĐIỀU KHIỂN GIAO DIỆN]:
${treeSkeleton}

DANH MỤC CÁC LỆNH ĐIỀU KHIỂN GIAO DIỆN BẠN CÓ THỂ RA LỆNH:
1. "keep_only_target": {"type": "keep_only_target", "chapter": 1, "section": "d", "item": "a1"} -> Giữ duy nhất mục này.
2. "keep_chapters_and_sections": {"type": "keep_chapters_and_sections", "chapters": [4], "targetChapter": 1, "sections": ["a", "b"]}
3. "set_only_chapters": {"type": "set_only_chapters", "chapters": [2, 3]}
4. "exclude_chapters": {"type": "exclude_chapters", "chapters": [1]}
5. "include_chapters": {"type": "include_chapters", "chapters": [1]}
6. "focus_chapter": {"type": "focus_chapter", "chapter": 1}
7. "open_editor": {"type": "open_editor", "chapter": 1}
8. "set_total_minutes": {"type": "set_total_minutes", "minutes": 10}
9. "set_chapter_duration": {"type": "set_chapter_duration", "chapter": 1, "seconds": 180}
10. "switch_tab": {"type": "switch_tab", "tab": "mindmap" | "script" | "video"}
11. "speak_narration": {"type": "speak_narration", "text": "Lời thoại..."}
12. "exclude_codes": {"type": "exclude_codes", "codes": ["1.1"]}
13. "include_codes": {"type": "include_codes", "codes": ["1.1"]}
14. "set_only_codes": {"type": "set_only_codes", "codes": ["1.1"]}
15. "focus_code": {"type": "focus_code", "code": "1.1"}
16. "speak_code": {"type": "speak_code", "code": "1.1"}
17. "set_node_config": {"type": "set_node_config", "code": "1.1", "voice": "Nam_MienNam", "speed": 1.25, "locked": true} -> Cài đặt giọng đọc, tốc độ, khóa cho mục.
18. "set_narration": {"type": "set_narration", "code": "1.1", "narration": "Kịch bản mới..."} -> Viết lại kịch bản lời thoại của mục.
19. "request_illustration": {"type": "request_illustration", "code": "1.1", "prompt": "mô tả hình ảnh"} -> Yêu cầu ảnh minh họa cho mục.

QUY TẮC:
1. NẾU NGƯỜI DÙNG HỎI KIẾN THỨC: Phải trả lời DỰA VÀO KIẾN THỨC ĐƯỢC RÚT TRÍCH ở trên. Nếu không có trong kiến thức rút trích, hãy nói là không tìm thấy. TUYỆT ĐỐI KHÔNG SINH RA JSON NẾU KHÔNG YÊU CẦU ĐIỀU KHIỂN UI!
2. NẾU NGƯỜI DÙNG YÊU CẦU ĐIỀU KHIỂN UI ("ẩn", "hiện", "chỉ giữ"): Kèm khối \`\`\`json ở cuối câu trả lời (như cũ).`;

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
