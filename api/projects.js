// Vercel Serverless Function: Cloud Projects Sync qua Neon Postgres
const { neon } = require('@neondatabase/serverless');

let tableInitialized = false;

function getDb() {
  const conn = process.env.STORAGE_URL || process.env.POSTGRES_URL || process.env.DATABASE_URL;
  if (!conn) return null;
  return neon(conn);
}

async function ensureTable(sql) {
  if (tableInitialized) return;
  await sql`
    CREATE TABLE IF NOT EXISTS clsg_projects (
      id VARCHAR(128) PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      data JSONB NOT NULL,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `;
  tableInitialized = true;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const sql = getDb();
  if (!sql) {
    return res.status(200).json({
      status: 'offline',
      connected: false,
      message: 'Chưa cấu hình biến môi trường kết nối Neon (STORAGE_URL / POSTGRES_URL) trên Vercel.'
    });
  }

  try {
    await ensureTable(sql);

    // 1. GET /api/projects
    if (req.method === 'GET') {
      const { id, ping } = req.query || {};

      if (ping === 'true') {
        await sql`SELECT 1 as ping;`;
        return res.status(200).json({ status: 'ok', connected: true, provider: 'Neon Serverless Postgres' });
      }

      if (id) {
        const rows = await sql`SELECT id, title, description, data, updated_at FROM clsg_projects WHERE id = ${id};`;
        if (rows.length === 0) {
          return res.status(404).json({ error: 'Không tìm thấy dự án trên Cloud' });
        }
        return res.status(200).json(rows[0]);
      }

      // Lấy toàn bộ danh sách dự án
      const rows = await sql`SELECT id, title, description, data, updated_at FROM clsg_projects ORDER BY updated_at DESC;`;
      return res.status(200).json(rows);
    }

    // 2. POST /api/projects: Lưu / Cập nhật dự án lên Cloud
    if (req.method === 'POST') {
      const body = (typeof req.body === 'string') ? JSON.parse(req.body) : (req.body || {});
      const id = body.id;
      const title = body.title || 'Dự Án Bài Giảng';
      const description = body.description || '';

      if (!id) {
        return res.status(400).json({ error: 'Thiếu ID dự án' });
      }

      // Xử lý lưu riêng Lịch sử Chat (nhanh, nhẹ, không ghi đè kịch bản)
      if (body.action === 'save_chat') {
        const chatHistory = body.chatHistory || [];
        const chatHtml = body.chatHtml || '';

        const updated = await sql`
          UPDATE clsg_projects
          SET data = jsonb_set(
            jsonb_set(COALESCE(data, '{}'::jsonb), '{chatHistory}', ${JSON.stringify(chatHistory)}::jsonb, true),
            '{chatHtml}', ${JSON.stringify(chatHtml)}::jsonb, true
          ),
          updated_at = CURRENT_TIMESTAMP
          WHERE id = ${id}
          RETURNING id;
        `;

        if (updated.length === 0) {
          const initialData = { id, title, description, chatHistory, chatHtml };
          await sql`
            INSERT INTO clsg_projects (id, title, description, data, updated_at)
            VALUES (${id}, ${title}, ${description}, ${JSON.stringify(initialData)}, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
              data = jsonb_set(
                jsonb_set(COALESCE(clsg_projects.data, '{}'::jsonb), '{chatHistory}', ${JSON.stringify(chatHistory)}::jsonb, true),
                '{chatHtml}', ${JSON.stringify(chatHtml)}::jsonb, true
              ),
              updated_at = CURRENT_TIMESTAMP;
          `;
        }
        return res.status(200).json({ status: 'ok', id, message: 'Đã lưu lịch sử chat lên Cloud Database' });
      }

      // Xử lý lưu riêng Tóm tắt & Tham số nhánh (nhanh, chuẩn xác)
      if (body.action === 'save_summaries' || body.action === 'save_node_params') {
        const nodeCustomParams = body.nodeCustomParams || {};
        const scenes = body.scenes || null;

        let updated;
        if (scenes) {
          updated = await sql`
            UPDATE clsg_projects
            SET data = jsonb_set(
              jsonb_set(COALESCE(data, '{}'::jsonb), '{nodeCustomParams}', ${JSON.stringify(nodeCustomParams)}::jsonb, true),
              '{scenes}', ${JSON.stringify(scenes)}::jsonb, true
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ${id}
            RETURNING id;
          `;
        } else {
          updated = await sql`
            UPDATE clsg_projects
            SET data = jsonb_set(COALESCE(data, '{}'::jsonb), '{nodeCustomParams}', ${JSON.stringify(nodeCustomParams)}::jsonb, true),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ${id}
            RETURNING id;
          `;
        }

        if (updated.length === 0) {
          const initialData = { id, title, description, nodeCustomParams, scenes: scenes || [] };
          await sql`
            INSERT INTO clsg_projects (id, title, description, data, updated_at)
            VALUES (${id}, ${title}, ${description}, ${JSON.stringify(initialData)}, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
              data = jsonb_set(COALESCE(clsg_projects.data, '{}'::jsonb), '{nodeCustomParams}', ${JSON.stringify(nodeCustomParams)}::jsonb, true),
              updated_at = CURRENT_TIMESTAMP;
          `;
        }
        return res.status(200).json({ status: 'ok', id, message: 'Đã lưu tóm tắt & tham số lên Cloud Database' });
      }

      // Xử lý lưu riêng Thông tin Video đã xuất theo Project & Loại (grid / tree)
      if (body.action === 'save_video_meta') {
        const videoType = body.videoType || 'grid';
        const videoMeta = body.videoMeta || {};

        let updated = await sql`
          UPDATE clsg_projects
          SET data = jsonb_set(
            COALESCE(data, '{}'::jsonb),
            ARRAY['videos', ${videoType}],
            ${JSON.stringify(videoMeta)}::jsonb,
            true
          ),
          updated_at = CURRENT_TIMESTAMP
          WHERE id = ${id}
          RETURNING id;
        `;

        if (updated.length === 0) {
          const initialData = { id, title, description, videos: { [videoType]: videoMeta } };
          await sql`
            INSERT INTO clsg_projects (id, title, description, data, updated_at)
            VALUES (${id}, ${title}, ${description}, ${JSON.stringify(initialData)}, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
              data = jsonb_set(
                COALESCE(clsg_projects.data, '{}'::jsonb),
                ARRAY['videos', ${videoType}],
                ${JSON.stringify(videoMeta)}::jsonb,
                true
              ),
              updated_at = CURRENT_TIMESTAMP;
          `;
        }
        return res.status(200).json({ status: 'ok', id, videoType, message: `Đã lưu thông tin video (${videoType}) lên Cloud Database` });
      }

      // Lưu toàn bộ dự án
      const dataPayload = body.data || body;

      await sql`
        INSERT INTO clsg_projects (id, title, description, data, updated_at)
        VALUES (${id}, ${title}, ${description}, ${JSON.stringify(dataPayload)}, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
          title = EXCLUDED.title,
          description = EXCLUDED.description,
          data = COALESCE(clsg_projects.data, '{}'::jsonb) || EXCLUDED.data,
          updated_at = CURRENT_TIMESTAMP;
      `;

      return res.status(200).json({ status: 'ok', id, message: 'Đã lưu lên Neon Cloud thành công' });
    }

    // 3. DELETE /api/projects?id=...: Xóa dự án trên Cloud
    if (req.method === 'DELETE') {
      const { id } = req.query || {};
      if (!id) {
        return res.status(400).json({ error: 'Thiếu ID dự án để xóa' });
      }

      await sql`DELETE FROM clsg_projects WHERE id = ${id};`;
      return res.status(200).json({ status: 'ok', deleted: id });
    }

    return res.status(405).json({ error: 'Method Not Allowed' });
  } catch (err) {
    console.error('[API Projects Error]', err);
    return res.status(500).json({ error: err.message || 'Lỗi xử lý cơ sở dữ liệu Neon' });
  }
};
