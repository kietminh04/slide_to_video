import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Define the start and end of the block to replace
start_marker = "function buildFullLectureContext() {"
end_marker = "if (res && res.ok) {"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    old_block = content[start_idx:end_idx]
    
    new_block = """function buildTreeSkeleton() {
        if (!activeProject) return '(Chưa có dự án bài giảng nào đang mở)';
        const roots = buildDecisionTree(activeProject, currentScenes);
        let out = `BÀI GIẢNG: "${activeProject.title}" (Tổng thời lượng: ${activeProject.duration_s || 300}s)\\n`;
        out += `MÔ TẢ: ${activeProject.desc || 'Không có mô tả'}\\n\\n`;
        out += `CẤU TRÚC PHÂN CẢNH, NHÁNH, LÁ:\\n`;

        roots.forEach((root) => {
          (root.children || []).forEach((chNode, cIdx) => {
            const chNum = cIdx + 1;
            const chTitle = chNode.data?.title || `Chương ${chNum}`;
            const chEx = isNodeExcluded(chNode.key);
            out += `\\n[CHƯƠNG ${chNum}]: "${chTitle}" (Trạng thái: ${chEx ? 'ĐÃ ẨN' : 'ĐANG DÙNG'})\\n`;

            (chNode.children || []).forEach((secNode, sIdx) => {
              const secCode = secNode.data?.code || `Phần ${String.fromCharCode(97 + sIdx)}`;
              const secTitle = secNode.data?.title || '';
              const secEx = isNodeExcluded(secNode.key, [chNode.key]);
              out += `  - [${secCode}]: "${secTitle}" (Trạng thái: ${secEx ? 'ẨN' : 'HIỆN'})\\n`;

              (secNode.children || []).forEach((itNode, iIdx) => {
                const itCode = itNode.data?.code || `item${iIdx + 1}`;
                const itTitle = itNode.data?.title || '';
                const itEx = isNodeExcluded(itNode.key, [chNode.key, secNode.key]);
                out += `      * Mục [${itCode}]: "${itTitle}" (Trạng thái: ${itEx ? 'ẨN' : 'HIỆN'})\\n`;
              });
            });
          });
        });
        return out;
      }

      try {
        const treeSkeleton = buildTreeSkeleton();
        const rollingHistory = clsgChatSessionHistory.slice(-6);

        let res = null;

        const payload = {
            projectId: currentProjectId,
            query: msg,
            history: rollingHistory,
            treeSkeleton: treeSkeleton
        };
        
        try {
          const serverUrl = (window.location.origin.startsWith('http') && !window.location.origin.includes('file:'))
            ? `${window.location.origin}/api/rag_chat`
            : '/api/rag_chat';
          const ctl = new AbortController();
          const tId = setTimeout(() => ctl.abort(), 55000);
          res = await fetch(serverUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: ctl.signal
          });
          clearTimeout(tId);
        } catch (e) {
          console.warn("[Copilot] Lỗi gọi Backend RAG:", e);
        }

        """
    
    content = content[:start_idx] + new_block + content[end_idx:]
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced RAG logic successfully!")
else:
    print("Could not find boundaries")
