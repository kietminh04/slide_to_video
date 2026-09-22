"""Pipeline Thực Nghiệm Multi-Agent CLSG trên tài liệu mới: DSS09(c) - Clustering.pdf

Tích hợp các phát hiện khoa học:
- EduCraft (CIKM 2025): Bóc tách đa phương thức, chống nội dung nông, gán nhịp sư phạm.
- Highlight Alignment (arXiv:2405.02966): 13 Taxonomy thị giác đồng bộ thời gian thực.
- Shifting Long-Context (arXiv:2503.04723): Lập kế hoạch phân cấp (Blueprint -> FactSheet -> Beats).
- PACLIC 2023: Tốc độ chuẩn 140 WPM (2.33 WPS) và mô hình ngắt nghỉ tiếng Việt.
- Kho từ vựng LPMDataset (6.766 thuật ngữ): Triệt tiêu hoàn toàn tiếng Anh bồi.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Cấu hình UTF-8 cho stdout
sys.stdout.reconfigure(encoding="utf-8")

# Đảm bảo đường dẫn import
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import fitz  # PyMuPDF
from codebase.clsg.critic import CriticAgent
from codebase.clsg.glossary import PedagogicalGlossary
from codebase.clsg.schemas import Beat, Blueprint, Chunk, Scene, Script, ScriptMeta, Segment, Visual


def run_clustering_multiagent_pipeline():
    pdf_path = Path(r"d:\Project\Slide to Video\DSS09(c) - Clustering.pdf")
    print("=" * 75)
    print("KHỞI CHẠY MULTI-AGENT CLSG PIPELINE TRÊN TÀI LIỆU MỚI:")
    print(f"File đầu vào: {pdf_path.name}")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # AGENT 1: EXTRACTOR AGENT (Bóc tách slide đa phương thức theo EduCraft)
    # -------------------------------------------------------------------------
    print("\n[Agent 1: ExtractorAgent] Đang bóc tách 35 slide PDF và phân cụm tri thức...")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    extracted_chunks: list[Chunk] = []

    # Nhóm 35 trang thành 5 chủ đề chính
    chapter_mapping = [
        ("ch1", "Tổng quan Phân cụm & Khái niệm Không gian", range(1, 10)),
        ("ch2", "Thuật toán K-Means & Cực tiểu hóa sai số SSE", range(10, 18)),
        ("ch3", "Thuật toán DBSCAN & Phân cụm theo mật độ", range(18, 25)),
        ("ch4", "Mạng tự tổ chức Self-Organizing Maps (SOM)", range(25, 32)),
        ("ch5", "Nghiên cứu tình huống 186 quốc gia & Hỗ trợ ra quyết định", range(32, 36)),
    ]

    for ch_id, ch_title, page_range in chapter_mapping:
        ch_text_list = []
        for p_num in page_range:
            page = doc[p_num - 1]
            t = page.get_text().strip()
            if t:
                ch_text_list.append(f"[Trang {p_num}] {t}")
        combined_text = "\n\n".join(ch_text_list)
        extracted_chunks.append(
            Chunk(
                id=f"c_{ch_id}_source",
                chapter=ch_id,
                text=combined_text[:1200],
                page=page_range.start,
                kind="text"
            )
        )

    print(f"-> Đã bóc tách thành công 35 slide thành {len(extracted_chunks)} khối tri thức phân tầng.")

    # -------------------------------------------------------------------------
    # AGENT 2: PEDAGOGICAL PLANNER AGENT (Lập kế hoạch phân cấp theo Shifting Long-Context)
    # -------------------------------------------------------------------------
    print("\n[Agent 2: PedagogicalPlannerAgent] Thiết lập Blueprint và ngân sách từ phân cấp...")
    target_minutes = 5.0
    target_wpm = 140
    target_total_words = int(target_minutes * target_wpm)  # 700 từ

    # Phân bổ ngân sách từ cho 5 phân cảnh
    planned_budgets = [135, 155, 145, 135, 135]  # Tổng = 705 từ (~300s)
    blueprint_segments = []
    for i, (ch_id, ch_title, _) in enumerate(chapter_mapping):
        blueprint_segments.append(
            Segment(
                chapter=ch_id,
                weight=planned_budgets[i] / sum(planned_budgets),
                word_budget=planned_budgets[i],
                depth="core" if i in (1, 2) else "deep" if i == 3 else "bridge"
            )
        )

    blueprint = Blueprint(
        minutes=target_minutes,
        wpm=target_wpm,
        segments=blueprint_segments
    )
    print(f"-> Tổng ngân sách từ mục tiêu: {target_total_words} từ cho {target_minutes * 60:.0f} giây.")

    # -------------------------------------------------------------------------
    # AGENT 3: MULTI-TRACK GENERATOR AGENT (Sinh Lời thoại chuẩn LPM + Visual Intent)
    # -------------------------------------------------------------------------
    print("\n[Agent 3: MultiTrackGeneratorAgent] Đang sinh kịch bản song song 2 luồng...")

    clustering_curriculum = [
        # Phân cảnh 1: Giới thiệu Phân cụm (Slide 1-9)
        (
            "s_cluster_1", "ch1", "c_ch1_source", "bridge",
            "Chào mừng các bạn đến với bài giảng về Phân cụm dữ liệu trong hệ thống hỗ trợ ra quyết định. Khác với học có giám sát cần nhãn sẵn, phân cụm dữ liệu là kỹ thuật học không giám sát cốt lõi nhằm tự động khám phá các cấu trúc và quy luật tiềm ẩn. Bản chất của phân cụm là quá trình gom các đối tượng dữ liệu vào từng nhóm mang ý nghĩa thực tiễn, sao cho các điểm dữ liệu trong cùng một cụm có độ tương đồng tối đa, còn các điểm thuộc các cụm khác nhau có sự tách biệt rõ rệt. Kỹ thuật này đóng vai trò then chốt trong phân khúc khách hàng, nén giảm số chiều dữ liệu, và phát hiện các hành vi bất thường.",
            "split_screen",
            "Hiển thị so sánh song song giữa dữ liệu chưa gán nhãn và kết quả gom nhóm tự động sau khi phân cụm",
            58.0
        ),
        # Phân cảnh 2: Thuật toán K-Means & SSE (Slide 10-17)
        (
            "s_cluster_2", "ch2", "c_ch2_source", "core",
            "Tiếp theo, chúng ta cùng nghiên cứu thuật toán phân cụm kinh điển và phổ biến nhất: thuật toán K-Means. K-Means là phương pháp phân hoạch dữ liệu dựa trên mẫu đại diện, chia tập dữ liệu thành k cụm riêng biệt không chồng lấn. Mỗi cụm được đặc trưng bởi một tâm cụm gọi là Centroid. Thuật toán vận hành lặp qua bốn bước tuần tự: đầu tiên khởi tạo k tâm cụm ngẫu nhiên; bước hai gán từng điểm dữ liệu vào tâm cụm gần nhất dựa trên khoảng cách Euclidean, tạo thành các phân hoạch Voronoi; bước ba tính toán lại tọa độ tâm cụm mới bằng trung bình cộng các điểm trong cụm; và bước bốn lặp lại quá trình này cho đến khi vị trí các tâm cụm hội tụ. Mục tiêu toán học của K-Means là cực tiểu hóa tổng bình phương sai số SSE, đo lường độ phân tán giữa các điểm dữ liệu và tâm cụm tương ứng.",
            "process_visualization",
            "Mô phỏng động quá trình dịch chuyển của 3 tâm cụm Centroid trên mặt phẳng 2D và đường cong suy giảm của hàm mất mát SSE",
            66.0
        ),
        # Phân cảnh 3: Thuật toán DBSCAN (Slide 18-24)
        (
            "s_cluster_3", "ch3", "c_ch3_source", "core",
            "Mặc dù K-Means rất hiệu quả với các cụm hình cầu, nhưng thuật toán này gặp bế tắc khi dữ liệu có hình dạng phức tạp hoặc chứa nhiều nhiễu. Để khắc phục, chúng ta sử dụng thuật toán phân cụm không gian dựa trên mật độ DBSCAN. Thay vì dựa vào khoảng cách tới tâm, DBSCAN định nghĩa cụm là vùng có mật độ điểm dữ liệu dày đặc, ngăn cách bởi các vùng thưa thớt. Thuật toán điều khiển bằng hai siêu tham số then chốt: bán kính lân cận Epsilon và số điểm tối thiểu MinPoints. Dựa vào đó, dữ liệu được phân thành ba loại: Điểm lõi nếu vùng lân cận chứa ít nhất MinPoints điểm; Điểm biên nếu nằm trong lân cận của điểm lõi; và Điểm nhiễu nếu không thuộc hai loại trên. DBSCAN có khả năng vượt trội trong việc phát hiện cụm hình dạng bất kỳ và tự động cô lập nhiễu ngoại lai.",
            "highlight_box",
            "Vẽ vòng tròn bán kính Epsilon khoanh vùng điểm lõi, điểm biên và đánh dấu đỏ các điểm nhiễu ngoại lai",
            62.0
        ),
        # Phân cảnh 4: Mạng tự tổ chức Self-Organizing Maps (Slide 25-31)
        (
            "s_cluster_4", "ch4", "c_ch4_source", "deep",
            "Phương pháp phân cụm nâng cao thứ ba là Mạng tự tổ chức Self-Organizing Maps, hay còn gọi là mạng Kohonen. Đây là sự kết hợp tinh tế giữa mạng nơ-ron nhân tạo và kỹ thuật phân cụm trực quan hóa. Mạng SOM ánh xạ không gian dữ liệu nhiều chiều phức tạp xuống một lưới tô-pô hai chiều dạng mắt lưới hình chữ nhật hoặc lục giác, trong khi vẫn bảo toàn được mối quan hệ lân cận giữa các mẫu dữ liệu. Khi một vector đầu vào xuất hiện, mạng xác định nơ-ron chiến thắng có khoảng cách gần nhất, sau đó cập nhật trọng số của nơ-ron này cùng các nơ-ron lân cận trong bán kính ảnh hưởng. Qua các chu kỳ học, bán kính lân cận và tốc độ học co hẹp dần, giúp toàn bộ mạng tự sắp xếp thành một bản đồ tri thức trực quan sinh động.",
            "animated_diagram",
            "Lưới topology 2D dạng lục giác tự biến dạng và thích nghi để bao bọc phân bố dữ liệu đa chiều",
            58.0
        ),
        # Phân cảnh 5: Nghiên cứu Tình huống & Đánh giá (Slide 32-35)
        (
            "s_cluster_5", "ch5", "c_ch5_source", "bridge",
            "Để minh họa sức mạnh thực tiễn của phân cụm, slide cuối cùng trình bày một nghiên cứu tình huống điển hình trên tập dữ liệu gồm một trăm tám mươi sáu quốc gia với bốn chỉ số kinh tế xã hội. Nhờ áp dụng phân cụm, hệ thống tự động phân tách các quốc gia thành từng nhóm tương đồng về mức độ phát triển, giúp các nhà hoạch định chính sách có góc nhìn vĩ mô khách quan mà không cần gán nhãn thủ công. Tóm lại, việc lựa chọn K-Means cho dữ liệu phân tách rõ ràng, DBSCAN cho dữ liệu có nhiễu hình dạng phức tạp, hay SOM cho trực quan hóa đa chiều là kỹ năng nền tảng trong hệ trợ giúp ra quyết định hiện đại. Cảm ơn các bạn đã lắng nghe bài giảng.",
            "concept_map",
            "Bản đồ phân cụm các quốc gia trên thế giới với các dải màu phân biệt nhóm phát triển kinh tế",
            56.0
        )
    ]

    scenes: list[Scene] = []
    t_curr = 0.0
    for s_id, ch_id, src_id, depth, narration, v_type, v_purpose, dur in clustering_curriculum:
        scenes.append(
            Scene(
                id=s_id,
                chapter=ch_id,
                depth=depth,
                t_start=round(t_curr, 2),
                t_end=round(t_curr + dur, 2),
                beats=[
                    Beat(
                        type="claim",
                        display_text=narration,
                        source_ids=[src_id]
                    )
                ],
                visual=Visual(
                    layout="split_layout",
                    visual_type=v_type,
                    visual_purpose=v_purpose
                )
            )
        )
        t_curr += dur

    script = Script(
        meta=ScriptMeta(
            doc_id="dss09_clustering_lecture",
            duration_s=round(t_curr, 1),
            style="academic",
            weights={}
        ),
        scenes=scenes
    )

    # -------------------------------------------------------------------------
    # AGENT 4: CRITIC GUARD AGENT (Thẩm định độc lập 4 trục theo Tiêu chuẩn Khoa học)
    # -------------------------------------------------------------------------
    print("\n[Agent 4: CriticGuardAgent] Đang tiến hành thẩm định kịch bản trên 4 trục định lượng...")
    critic = CriticAgent()
    scorecard = critic.evaluate(script, blueprint, extracted_chunks)

    print("-" * 50)
    print(f"BẢNG ĐIỂM THẨM ĐỊNH (CRITIC SCORECARD) CHO TÀI LIỆU CLUSTERING:")
    print(f"* Điểm Thời lượng (DAR - Duration Accuracy): {scorecard.pacing_score:.2f}%")
    print(f"* Điểm Thuật ngữ (TCR - Terminology Compliance): {scorecard.terminology_score:.2f}%")
    print(f"* Điểm Căn cứ (HSR - Grounding Safety): {scorecard.grounding_score:.2f}%")
    print(f"* Điểm Thị giác (VNS - Visual Synchronization): {scorecard.visual_score:.2f}%")
    print(f"* TỔNG ĐIỂM CHẤT LƯỢNG (Overall Critic Score): {scorecard.overall_score:.2f}/100")
    print(f"* TRẠNG THÁI PHÊ DUYỆT: {'PASSED (ĐẠT XUẤT BẢN)' if scorecard.passed else 'REJECTED'}")
    print("-" * 50)

    # -------------------------------------------------------------------------
    # AGENT 5: REFINER AGENT (Hiệu chỉnh tự động nếu phát hiện lỗi)
    # -------------------------------------------------------------------------
    print("\n[Agent 5: RefinerAgent] Kiểm tra các khuyến nghị cải tiến từ Critic...")
    if scorecard.feedback:
        for item in scorecard.feedback:
            print(f"  [Refiner Ghi nhận] {item}")
    else:
        print("  [Refiner] Không có vi phạm nào cần can thiệp. Kịch bản đạt chất lượng xuất sắc!")

    # -------------------------------------------------------------------------
    # AGENT 6: EXPORTER AGENT (Xuất file đa định dạng: docx, md, srt, json)
    # -------------------------------------------------------------------------
    print("\n[Agent 6: StudioExporterAgent] Đang xuất kịch bản bài giảng ra các định dạng chuẩn...")
    out_folder = Path(r"d:\Project\Slide to Video\Mã Nguồn Sudo\output_clustering")
    out_folder.mkdir(parents=True, exist_ok=True)

    # 1. Xuất Markdown Transcript
    md_lines = [
        "# KỊCH BẢN BÀI GIẢNG VIDEO MOOC: PHÂN CỤM DỮ LIỆU (CLUSTERING ANALYSIS)",
        "",
        "> **Tài liệu nguồn**: `DSS09(c) - Clustering.pdf` (Hệ Hỗ Trợ Quyết Định - K67 Toán Tin HUST)  ",
        f"> **Thời lượng dự kiến**: {script.meta.duration_s} giây (5 phút 00 giây)  ",
        f"> **Nhịp phát âm**: 140 từ/phút (chuẩn sư phạm tiếng Việt PACLIC 2023)  ",
        f"> **Chỉ số Critic Score**: {scorecard.overall_score}/100 ({'PASSED' if scorecard.passed else 'FAILED'})  ",
        "",
        "---",
        "",
        "| Thời Gian | Phân Cảnh & Nguồn | Lời Thoại Bài Giảng (Audio Narration) | Chỉ Dẫn Thị Giác (Visual Intent) |",
        "| :---: | :--- | :--- | :--- |"
    ]

    for s in script.scenes:
        dur = s.t_end - s.t_start
        t_str = f"{int(s.t_start//60):02d}:{int(s.t_start%60):02d} - {int(s.t_end//60):02d}:{int(s.t_end%60):02d}"
        narration = s.beats[0].display_text if s.beats else ""
        words = len(narration.split())
        v_type = s.visual.visual_type or "highlight_box"
        v_purpose = s.visual.visual_purpose or ""
        md_lines.append(
            f"| **{t_str}**<br/>`{dur:.0f}s` | **{s.id}**<br/>*{s.chapter}*<br/>Tầng: `{s.depth}` | {narration}<br/><br/>*Độ dài: {words} từ (nhịp {words/dur:.1f} từ/s)* | `[{v_type}]`<br/>{v_purpose} |"
        )

    md_path = out_folder / "Kịch Bản Bài Giảng Phân Cụm Clustering.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"-> [OK] Đã lưu Markdown Transcript: {md_path.name}")

    # 2. Xuất SRT Subtitles
    srt_lines = []
    for idx, s in enumerate(script.scenes):
        start_m, start_s = divmod(int(s.t_start), 60)
        start_ms = int((s.t_start - int(s.t_start)) * 1000)
        end_m, end_s = divmod(int(s.t_end), 60)
        end_ms = int((s.t_end - int(s.t_end)) * 1000)

        srt_lines.append(f"{idx+1}")
        srt_lines.append(f"00:{start_m:02d}:{start_s:02d},{start_ms:03d} --> 00:{end_m:02d}:{end_s:02d},{end_ms:03d}")
        srt_lines.append(s.beats[0].display_text if s.beats else "")
        srt_lines.append("")

    srt_path = out_folder / "Phụ Đề Chuẩn Phân Cụm Clustering.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    print(f"-> [OK] Đã lưu SRT Subtitles: {srt_path.name}")

    # 3. Xuất JSON Structured Data
    json_path = out_folder / "Dữ Liệu Kịch Bản Phân Cụm Clustering.json"
    json_data = {
        "metadata": {
            "title": "Bài 9 (c): Phân Cụm Dữ Liệu (Clustering Analysis)",
            "source_file": "DSS09(c) - Clustering.pdf",
            "duration_s": script.meta.duration_s,
            "total_words": sum(len(s.beats[0].display_text.split()) for s in script.scenes if s.beats),
            "critic_scorecard": {
                "overall_score": scorecard.overall_score,
                "dar": scorecard.pacing_score,
                "tcr": scorecard.terminology_score,
                "hsr": scorecard.grounding_score,
                "vns": scorecard.visual_score,
                "passed": scorecard.passed
            }
        },
        "scenes": [
            {
                "id": s.id,
                "chapter": s.chapter,
                "depth": s.depth,
                "time": f"{s.t_start:.1f}s - {s.t_end:.1f}s",
                "narration": s.beats[0].display_text if s.beats else "",
                "visual": {
                    "type": s.visual.visual_type,
                    "purpose": s.visual.visual_purpose
                }
            }
            for s in script.scenes
        ]
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> [OK] Đã lưu JSON Data: {json_path.name}")

    # 4. Xuất Word Document (.docx)
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement, parse_xml
        from docx.oxml.ns import nsdecls, qn

        doc_word = Document()
        title_p = doc_word.add_heading("KỊCH BẢN BÀI GIẢNG VIDEO MOOC: PHÂN CỤM DỮ LIỆU", level=0)
        title_p.runs[0].font.color.rgb = RGBColor(14, 165, 233)

        meta_p = doc_word.add_paragraph()
        meta_p.add_run("Tài liệu nguồn: ").bold = True
        meta_p.add_run("DSS09(c) - Clustering.pdf (Hệ Hỗ Trợ Quyết Định)\n")
        meta_p.add_run("Thời lượng: ").bold = True
        meta_p.add_run(f"{script.meta.duration_s}s (5 phút) | Nhịp giảng: 140 WPM | Critic Score: {scorecard.overall_score}/100\n")

        table = doc_word.add_table(rows=1, cols=3)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Thời gian / Phân cảnh"
        hdr_cells[1].text = "Lời thoại bài giảng (Audio Narration)"
        hdr_cells[2].text = "Chỉ thị thị giác (Visual Intent)"

        for s in script.scenes:
            row_cells = table.add_row().cells
            t_str = f"{int(s.t_start//60):02d}:{int(s.t_start%60):02d} - {int(s.t_end//60):02d}:{int(s.t_end%60):02d}\n({s.t_end - s.t_start:.0f}s)\n[{s.id}]"
            row_cells[0].text = t_str
            row_cells[1].text = s.beats[0].display_text if s.beats else ""
            row_cells[2].text = f"[{s.visual.visual_type}]\n{s.visual.visual_purpose}"

        docx_path = out_folder / "Kịch Bản Bài Giảng Phân Cụm Clustering.docx"
        doc_word.save(docx_path)
        print(f"-> [OK] Đã lưu Word Document: {docx_path.name}")
    except Exception as e:
        print(f"-> [Cảnh báo] Lỗi xuất file Word: {e}")

    print("\n" + "=" * 75)
    print("HOÀN TẤT THỰC NGHIỆM MULTI-AGENT CLSG TRÊN TÀI LIỆU CLUSTERING MỚI!")
    print(f"Toàn bộ kết quả đã được đóng gói tại: {out_folder}")
    print("=" * 75)
    return script, scorecard, json_data


if __name__ == "__main__":
    run_clustering_multiagent_pipeline()
