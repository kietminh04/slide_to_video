import sys

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """<label class="source-drop-zone" id="source-drop-zone" for="source-file-input">
<div style="font-size: 26px; margin-bottom: 4px;">📂</div>
<div style="font-size: 12px; font-weight: 700; color: var(--text-main);">+ Thêm Tài Liệu</div>
<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">Kéo thả hoặc bấm để nạp .pdf, .pptx,
.docx</div>
<input type="file" id="source-file-input" accept=".pptx,.pdf,.docx,.txt" style="display: none;">
</label>

<!-- TOGGLE VISION OCR -->
<div style="margin-top: 8px; display: flex; align-items: center; justify-content: center; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 6px;">
  <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;" title="Sử dụng Vision API để quét và bóc tách các file PDF/PPTX chứa ảnh tĩnh (không có text)">
    <input type="checkbox" id="use-visual-ocr" style="accent-color: var(--cyan); width: 14px; height: 14px;" />
    <span style="font-size: 11px; font-weight: 600; color: var(--cyan);">👁️ Quét Ảnh Slide (Vision AI)</span>
  </label>
</div>"""

target = """<label class="source-drop-zone" id="source-drop-zone" for="source-file-input">
<div style="font-size: 26px; margin-bottom: 4px;">📂</div>
<div style="font-size: 12px; font-weight: 700; color: var(--text-main);">+ Thêm Tài Liệu</div>
<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">Kéo thả hoặc bấm để nạp .pdf, .pptx,
.docx</div>
<input type="file" id="source-file-input" accept=".pptx,.pdf,.docx,.txt" style="display: none;">
</label>"""

if target in content:
    content = content.replace(target, replacement)
    
    js_addition = """    async function extractVisualSlideStructure(file) {
      updateLoading("Đang phân tích ảnh slide bằng Vision AI...", "Đang bóc tách kiến thức toàn bộ bài giảng qua API Backend...");
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch('http://localhost:8081/api/extract-visual-slides', {
          method: 'POST',
          body: formData
        });
        if (!response.ok) throw new Error("Lỗi API Vision OCR: " + response.statusText);
        const data = await response.json();
        if (data.success && data.chapters && data.chapters.length > 0) {
          hideLoading();
          return {
            title: (file.name || '').replace(/\\.[^/.]+$/, ""),
            totalPages: data.total_pages,
            chapters: data.chapters,
            method: 'vision-ocr'
          };
        }
      } catch (err) {
        console.error("Lỗi extractVisualSlideStructure:", err);
      }
      hideLoading();
      return null;
    }

    async function extractDocumentStructure(file) {"""
    
    js_target = "async function extractDocumentStructure(file) {"
    
    if js_target in content:
        content = content.replace(js_target, js_addition)
        
        js_logic_add = """    async function extractDocumentStructure(file) {
      const useOcrChk = document.getElementById('use-visual-ocr');
      if (useOcrChk && useOcrChk.checked) {
          const visualData = await extractVisualSlideStructure(file);
          if (visualData) return visualData;
      }"""
        content = content.replace("async function extractDocumentStructure(file) {", js_logic_add)
        
        with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated index.html")
    else:
        print("Could not find extractDocumentStructure function")
else:
    print("Could not find drop zone target")
