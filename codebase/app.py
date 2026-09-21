"""Streamlit UI cho CLSG Script Engine.

Chú ý: file này nằm NGOÀI clsg/ vì clsg/ là thư viện thuần.
Chỉ gọi engine.run_pipeline, không import nội tạng pipeline.
"""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="CLSG Script Engine", layout="wide")
st.title("🎬 CLSG Script Engine")
st.caption("Sinh kịch bản video bài giảng có trọng số theo chương")

# === Sidebar ===
with st.sidebar:
    st.header("⚙️ Cấu hình")
    uploaded_doc = st.file_uploader("Tài liệu nguồn", type=["txt", "pdf", "docx", "pptx"])
    uploaded_weights = st.file_uploader("File trọng số (JSON)", type=["json"])
    style_pack = st.selectbox("Style pack", ["serious", "drama_tongtai"])
    use_fake = st.checkbox("Dùng FakeLLMProvider (test)", value=True)
    run_btn = st.button("🚀 Sinh kịch bản", type="primary")

# === Main ===
if run_btn and uploaded_doc and uploaded_weights:
    from codebase.clsg.engine import run_pipeline

    # Lưu file tạm
    tmp_dir = Path("_tmp_streamlit")
    tmp_dir.mkdir(exist_ok=True)

    doc_path = tmp_dir / uploaded_doc.name
    doc_path.write_bytes(uploaded_doc.read())

    weights_path = tmp_dir / "weights.json"
    weights_path.write_text(
        uploaded_weights.read().decode("utf-8"), encoding="utf-8"
    )

    with st.spinner("Đang sinh kịch bản..."):
        script = run_pipeline(
            doc_path=doc_path,
            weights_path=weights_path,
            fake=use_fake,
            style_pack=style_pack,
        )

    # Hiển thị kết quả
    st.success(f"✅ {len(script.scenes)} scene")

    for scene in script.scenes:
        with st.expander(f"Scene {scene.id} ({scene.depth}) – {scene.chapter}"):
            for beat in scene.beats:
                icon = {
                    "claim": "📌", "bridge": "🌉", "example": "💡",
                    "flavor": "🎭", "question": "❓",
                }
                st.markdown(f"{icon.get(beat.type, '•')} **{beat.type}**: {beat.display_text}")

    # JSON
    with st.expander("📄 JSON"):
        st.json(json.loads(script.model_dump_json()))
elif run_btn:
    st.warning("Vui lòng upload tài liệu và file trọng số.")
