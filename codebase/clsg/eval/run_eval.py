import datetime
import json
import os
from pathlib import Path
from typing import Any

# Giả định engine.run_pipeline có chữ ký:
# run_pipeline(doc_id: str, chunks: list[Chunk], weights: dict[str, float], llm_provider: Any, **kwargs) -> Script
from codebase.clsg.engine import run_pipeline
from codebase.clsg.eval.baseline import BaselineGenerator
from codebase.clsg.eval.metrics import calculate_all_metrics
from codebase.clsg.schemas import Chunk

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

def load_or_create_dummy_data() -> dict[str, dict]:
    """Tải dữ liệu từ eval/data/ hoặc tạo dữ liệu giả nếu thư mục rỗng."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cases = {}

    # Thử đọc các file json trong data/
    for file in DATA_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            cases[file.stem] = json.load(f)

    if not cases:
        # Tạo dữ liệu giả
        dummy_chunks = [
            Chunk(id="c1", chapter="ch1", text="Đây là nội dung cốt lõi của chương 1, giải thích về cơ học lượng tử."),
            Chunk(id="c2", chapter="ch1", text="Ví dụ về hạt trong hộp."),
            Chunk(id="c3", chapter="ch2", text="Chương 2 nói về thuyết tương đối hẹp của Einstein."),
            Chunk(id="c4", chapter="ch2", text="Công thức E=mc^2 là một hệ quả nổi tiếng."),
        ]

        cases["dummy_case"] = {
            "doc_id": "dummy_doc",
            "chunks": [c.model_dump() for c in dummy_chunks],
            "weights_focus": {"ch1": 0.7, "ch2": 0.3},
            "weights_even": {"ch1": 0.5, "ch2": 0.5},
        }

        with open(DATA_DIR / "dummy_case.json", "w", encoding="utf-8") as f:
            json.dump(cases["dummy_case"], f, ensure_ascii=False, indent=2)

    return cases

def generate_markdown_report(results: dict) -> str:
    """Tạo bảng Markdown từ kết quả JSON."""
    md = "## Kết quả Đánh giá\n\n"
    md += "| Case | Hệ thống | Trọng số (L1) | Phủ (Coverage) | Copy Ratio | Specificity |\n"
    md += "|---|---|---|---|---|---|\n"

    for case_name, case_results in results.items():
        for sys_name, metrics in case_results.items():
            l1 = metrics.get("allocation_l1", 0)
            cov = metrics.get("required_coverage", 0)
            copy = metrics.get("copy_ratio", 0)
            spec = metrics.get("specificity", 0)
            md += f"| {case_name} | {sys_name} | {l1:.3f} | {cov:.3f} | {copy:.3f} | {spec:.3f} |\n"

    return md

def run_eval(llm_provider: Any):
    """Chạy đánh giá cho các hệ thống: baseline, pipeline gốc, pipeline ablation."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cases = load_or_create_dummy_data()

    baseline_gen = BaselineGenerator(llm_provider)

    all_results = {}

    for case_name, data in cases.items():
        print(f"Đang chạy đánh giá cho case: {case_name}")
        doc_id = data["doc_id"]
        chunks = [Chunk(**c) for c in data["chunks"]]
        weights_focus = data.get("weights_focus", {"ch1": 0.5, "ch2": 0.5})
        weights_even = data.get("weights_even", {"ch1": 0.5, "ch2": 0.5})

        case_results = {}

        # 1. Baseline (dùng trọng số lệch)
        try:
            script_baseline = baseline_gen.generate(doc_id, chunks, weights_focus)
            case_results["baseline"] = calculate_all_metrics(script_baseline, chunks)
        except Exception as e:
            print(f"Lỗi chạy baseline: {e}")
            case_results["baseline"] = {"error": str(e)}

        # 2. Pipeline gốc (dùng trọng số lệch)
        try:
            script_pipeline = run_pipeline(doc_id=doc_id, chunks=chunks, weights=weights_focus, llm_provider=llm_provider)
            case_results["pipeline"] = calculate_all_metrics(script_pipeline, chunks)
        except Exception as e:
            print(f"Lỗi chạy pipeline gốc: {e}")
            case_results["pipeline"] = {"error": str(e)}

        # 3. Pipeline ablation (tắt trọng số - dùng trọng số đều)
        try:
            script_ablation = run_pipeline(doc_id=doc_id, chunks=chunks, weights=weights_even, llm_provider=llm_provider)
            case_results["ablation"] = calculate_all_metrics(script_ablation, chunks)
        except Exception as e:
            print(f"Lỗi chạy ablation: {e}")
            case_results["ablation"] = {"error": str(e)}

        all_results[case_name] = case_results

    # Ghi kết quả JSON
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"results_{date_str}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Tạo và in Markdown
    md_report = generate_markdown_report(all_results)
    print("\n" + md_report)

    # Cập nhật REPORT.md
    report_path = Path(__file__).parent.parent.parent.parent / "REPORT.md"
    if not report_path.exists():
        report_path = RESULTS_DIR / "REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    return all_results

if __name__ == "__main__":
    # Điểm chạm cho việc chạy thực tế, thay FakeLLMProvider bằng LLM thật khi cần
    from codebase.clsg.llm import LLMProvider  # Giả định
    llm = LLMProvider()
    run_eval(llm)
