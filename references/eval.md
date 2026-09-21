# Eval tham chiếu (`eval/`)

Đọc file này khi viết hoặc sửa bộ đánh giá.

## Dữ liệu

- 5 tài liệu có giấy phép mở hoặc được giảng viên đồng ý, mỗi tài liệu 2 file trọng số: đều, và lệch 0,7 về một chương. Tổng 10 ca.
- Mỗi chương trọng tâm có 5 câu hỏi dạng "vì sao" hoặc "như thế nào", sinh từ chunk nguồn rồi được người duyệt.
- Vài ca đối kháng: PDF scan, slide toàn hình, tài liệu cài prompt injection, trọng số toàn 0. Kỳ vọng là từ chối rõ ràng hoặc gắn cờ, không sinh bừa.

## Hệ so sánh

1. Baseline: một prompt duy nhất "viết kịch bản 5 phút từ tài liệu này", output ép về cùng schema `Script`.
2. Pipeline đầy đủ.
3. Ablation: pipeline tắt trọng số (trọng số đều, `focus=1`).

## Metric tự động (`metrics.py`, mỗi metric một hàm nhận `Script` và `list[Chunk]`)

| Metric | Cách tính | Mục tiêu đề xuất |
| --- | --- | --- |
| `allocation_l1` | L1 giữa tỉ lệ từ theo chương và trọng số | ≤ 0,15 |
| `required_coverage` | chunk trong blueprint được dẫn / tổng | ≥ 0,9 |
| `claim_supported_rate` | claim được judge là supported / tổng claim; kiểm tra tay 10% | ≥ 0,95, không có contradicted |
| `specificity` | (ví dụ + con số + câu nhân quả) trên 100 từ ở đoạn deep | cao hơn baseline |
| `copy_ratio` | tỉ lệ 5-gram trùng nguồn | ≤ 0,3 |
| `claims_lost_after_style` | claim có trước style nhưng mất sau style | 0 |
| `why_qa` | model khác chỉ đọc kịch bản, trả lời 5 câu "vì sao"; judge chấm đúng/sai so với chunk | cao hơn baseline |
| `cost_usd`, `latency_s` | từ log usage JSONL; báo trung vị và p95 | ghi nhận, có trần |

Mục tiêu là đề xuất; chốt lại sau khi đo baseline. Không ghi số chưa đo vào báo cáo.

## Chấm bằng LLM

- Chấm theo từng đoạn ngắn, không chấm cả kịch bản một lượt, vì judge bỏ sót lỗi logic ở văn bản dài.
- Judge khác model sinh. Chấm theo cặp thì đảo thứ tự A/B ngẫu nhiên để tránh thiên vị vị trí.
- Hiệu chuẩn: một mẫu nhỏ (30–50 đoạn) do 2 người chấm; chỉ tin judge khi đồng thuận với người đạt mức chấp nhận được (ví dụ Cohen's kappa ≥ 0,6). Nếu không kịp hiệu chuẩn, ghi rõ hạn chế này trong `REPORT.md`.

## Chấm bằng người

3–5 người xem mù cặp kịch bản A/B cho cùng tài liệu, chấm "sâu" và "hấp dẫn" thang 1–5. Lưu phiếu thô vào `validation/`. Cỡ mẫu này chỉ cho tín hiệu định hướng; nói rõ điều đó.

## Đầu ra

`run_eval.py` chạy một lệnh, ghi `results/<ngày>.json` gồm metric theo từng ca và từng hệ, và sinh bảng tổng hợp cho `REPORT.md`. Trên CI chỉ chạy tập con 2 ca với `FakeLLMProvider` để kiểm tra code eval không vỡ; chạy thật bằng tay trước mỗi mốc.
