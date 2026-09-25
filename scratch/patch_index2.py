import sys

with open(r'd:\Project\Slide to Video\Mã Nguồn Sudo\index.html', 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

for i in range(len(lines)):
    if 'id="source-file-input"' in lines[i]:
        # found the input line, let's inject after the closing label
        for j in range(i, i+10):
            if '</label>' in lines[j]:
                # inject here
                lines.insert(j+1, """
<!-- TOGGLE VISION OCR -->
<div style="margin-top: 8px; display: flex; align-items: center; justify-content: center; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 6px;">
  <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;" title="Sử dụng Vision API để quét và bóc tách các file PDF/PPTX chứa ảnh tĩnh (không có text)">
    <input type="checkbox" id="use-visual-ocr" style="accent-color: var(--cyan); width: 14px; height: 14px;" />
    <span style="font-size: 11px; font-weight: 600; color: var(--cyan);">👁️ Quét Ảnh Slide (Vision AI)</span>
  </label>
</div>""")
                break
        break

content = '\n'.join(lines)

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
    print("Updated index.html successfully")
else:
    print("Could not find extractDocumentStructure function")
