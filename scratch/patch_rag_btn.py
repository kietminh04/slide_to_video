import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Button
btn_str = """<button class="mindmap-ctrl-btn" id="btn-ai-refactor-mindmap"
              style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(168, 85, 247, 0.4)); border: 1px solid rgba(168, 85, 247, 0.7); color: #fff; font-weight: 700; padding: 0 14px; gap: 6px; display: flex; align-items: center;"
              title="Phân tích lại toàn bộ bài giảng và chuẩn hóa sơ đồ tư duy">
              <span>🧠</span> Tái Cấu Trúc Sơ Đồ
            </button>"""

new_btn_str = btn_str + """
            <button class="mindmap-ctrl-btn" id="btn-rag-ingest"
              style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.4), rgba(5, 150, 105, 0.4)); border: 1px solid rgba(16, 185, 129, 0.7); color: #fff; font-weight: 700; padding: 0 14px; gap: 6px; display: flex; align-items: center; margin-left: 8px;"
              title="Nạp kiến thức sơ đồ vào Cơ sở dữ liệu Vector để Chatbot hỏi đáp chuẩn xác">
              <span>📚</span> Nạp Tri Thức RAG
            </button>"""

if btn_str in content:
    content = content.replace(btn_str, new_btn_str)
else:
    print("Cannot find button to replace")

# 2. Add Function and Event Listener at the bottom
js_injection = """
    // --- BẮT ĐẦU: RAG INGESTION TÍCH HỢP ---
    async function triggerRagIngestion() {
      if (!activeProject || !currentProjectId) {
        showToast('⚠️ Vui lòng mở một dự án trước khi nạp tri thức!');
        return;
      }
      if (!activeProject.scenes || activeProject.scenes.length === 0) {
        showToast('⚠️ Dự án chưa có sơ đồ bài giảng nào để nạp!');
        return;
      }

      const btn = document.getElementById('btn-rag-ingest');
      const originalHtml = btn ? btn.innerHTML : '<span>📚</span> Nạp Tri Thức RAG';
      if (btn) {
        btn.innerHTML = '<span>⏳</span> Đang Nạp Vector...';
        btn.disabled = true;
      }

      try {
        showToast('Đang nạp tri thức bài giảng vào Database...');
        
        let chunks = [];
        activeProject.scenes.forEach(scene => {
          if (!scene.beats) return;
          scene.beats.forEach(beat => {
            const content = [beat.details, beat.mechanism, beat.key_point, beat.summary].filter(Boolean).join('. ');
            if (content.length > 20) {
              chunks.push({
                chapter_name: scene.title,
                section_name: beat.title,
                text: content
              });
            }
          });
        });

        if (chunks.length === 0) {
            showToast('⚠️ Sơ đồ trống, không có văn bản nào đủ dài để nạp.');
            if(btn) {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
            }
            return;
        }

        const response = await fetch('/api/rag_ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            projectId: currentProjectId, 
            chunks: chunks 
          })
        });

        const data = await response.json();
        if (data.success) {
          showToast(`✅ Đã nạp thành công ${data.processed || chunks.length} Vector vào Neon DB! Chatbot đã thông minh hơn.`);
        } else {
          console.error(data.error);
          showToast(`❌ Lỗi khi nạp: ${data.error}`);
        }
      } catch (err) {
        console.error("Lỗi Ingestion:", err);
        showToast('❌ Lỗi kết nối đến Backend Ingestion.');
      } finally {
        if (btn) {
          btn.innerHTML = originalHtml;
          btn.disabled = false;
        }
      }
    }

    document.getElementById('btn-rag-ingest')?.addEventListener('click', triggerRagIngestion);
    // --- KẾT THÚC: RAG INGESTION TÍCH HỢP ---

    // INITIALIZE PROJECTS DASHBOARD & KHÔI PHỤC VIEW ĐANG LÀM VIỆC (KHÔNG BỊ QUAY VỀ TRANG ĐẦU)
"""

if "    // INITIALIZE PROJECTS DASHBOARD & KHÔI PHỤC VIEW ĐANG LÀM VIỆC (KHÔNG BỊ QUAY VỀ TRANG ĐẦU)" in content:
    content = content.replace("    // INITIALIZE PROJECTS DASHBOARD & KHÔI PHỤC VIEW ĐANG LÀM VIỆC (KHÔNG BỊ QUAY VỀ TRANG ĐẦU)", js_injection)
else:
    print("Cannot find init line")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched index.html with RAG Ingest Button!")
