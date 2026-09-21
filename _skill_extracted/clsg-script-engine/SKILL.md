---
name: clsg-script-engine
description: Thiết kế và xây dựng CLSG script engine, hệ thống sinh kịch bản video bài giảng có trọng số theo chương cho MOOC (tài liệu PPTX/DOCX/PDF + trọng số chương → script.json có dẫn nguồn và timeline). Dùng skill này bất cứ khi nào làm việc trong repo CLSG hoặc khi người dùng nhắc tới sinh kịch bản bài giảng, lecture script generation, weighted planner, ngân sách từ, word budget, độ sâu deep/core/bridge, phiếu dữ kiện (fact sheet), guard nhịp độ hoặc sự thật, style pack (tổng tài, meme), eval so với baseline một prompt, hay cấu trúc repo cho hackathon này, kể cả khi họ không gọi tên "CLSG".
---

# CLSG Script Engine

Skill này giúp bạn thiết kế và viết code cho một script engine: nhận tài liệu học và vector trọng số theo chương, xuất `script.json` cho video bài giảng 5 phút tiếng Việt. Bối cảnh là hackathon 3 ngày, nhóm 5 người, nhưng code phải lên product được mà không viết lại.

Phạm vi 3 ngày **chỉ là viết kịch bản**. Không làm TTS, không render video, không database. Nếu người dùng yêu cầu những thứ đó, hãy nhắc phạm vi và hỏi lại trước khi làm.

## Vấn đề cốt lõi cần giải

Khi đưa cả tài liệu cho LLM và bảo "làm video 5 phút", model hiểu đó là bài tóm tắt và rải đều lời cho mọi mục, nên kết quả nông. Engine này đổi bài toán thành "dạy N điểm đã chọn, mỗi điểm theo một khuôn bắt buộc". Độ sâu đến từ việc dám bỏ bớt, và trọng số quyết định bỏ cái gì. Mọi quyết định thiết kế bên dưới phục vụ ý này; khi phân vân, hãy chọn phương án giữ được nó.

## Ba ranh giới không được phá

Đây là lý do MVP lên product được. Nếu một thay đổi buộc phải phá một trong ba, dừng lại và nói với người dùng.

1. **`clsg/` là thư viện thuần.** Không import Streamlit, Typer hay bất kỳ thứ gì của UI. Phép thử: `python -m cli generate ...` chạy được khi chưa cài Streamlit.
2. **Mọi dữ liệu giữa các module là Pydantic model trong `schemas.py`.** Không truyền dict trần. Schema là hợp đồng giữa 5 người làm song song.
3. **Mọi thứ bên ngoài nằm sau interface.** LLM đi qua `LLMProvider`, được truyền vào hàm qua tham số, không khởi tạo bên trong module. Nhờ vậy test dùng `FakeLLMProvider` và CI không tốn tiền.

## Pipeline

```
extract(path) -> list[Chunk]                         code thuần, zero-LLM
plan(chunks, WeightProfile, settings, llm) -> Blueprint
    weights -> word budget -> teaching points -> depth   code thuần
    chọn TeachingPoint kèm chunk_ids                     1 lời gọi LLM
generate(blueprint, chunks, llm) -> list[Scene]
    mỗi đoạn: factsheet (LLM) -> write beats (LLM)
guard(script, chunks, llm_judge) -> GuardReport
    nhịp, phân bổ, độ sâu                                code thuần
    sự thật từng claim                                   LLM khác model sinh
    đoạn rớt -> sinh lại, tối đa 2 vòng
style(script, pack, llm) -> Script                   chỉ thêm beat flavor, rồi chạy lại guard
timeline(script) -> Script                           est_s từ số âm tiết, cộng dồn t_start/t_end
```

Nguyên tắc chọn chỗ đặt LLM: **LLM cho việc cần hiểu nghĩa, code cho việc đếm được.** Không để LLM đếm từ, tính trọng số, hay tự chấm output của chính nó. Điểm quiz thô của học viên không bao giờ đi vào prompt; pipeline chỉ nhận vector trọng số.

## Cấu trúc repo MVP

Mỗi module một file. Khi file vượt khoảng 300 dòng thì tách thành thư mục cùng tên và giữ nguyên tên hàm public.

```
codebase/
  clsg/
    schemas.py    config.py    llm.py
    extract.py    plan.py      generate.py
    guard.py      style.py     engine.py
    prompts/      # select.j2 factsheet.j2 write.j2 judge.j2 style.j2
    packs/        # serious.yaml drama_tongtai.yaml
  cli.py          # Typer
  app.py          # Streamlit, chỉ gọi engine.generate
  fixtures/       # script_sample.json, 1 tài liệu mẫu, weights.json
  tests/          # test_plan.py test_guard.py test_engine_fake.py
eval/
  data/  baseline.py  metrics.py  run_eval.py  REPORT.md
evidence/  validation/  spec.md  Dockerfile  pyproject.toml
```

Chiều phụ thuộc một hướng: `schemas` không import gì; module nghiệp vụ import `schemas` và `llm`; chỉ `engine.py` biết thứ tự các bước. `eval/` chỉ gọi `engine.generate` và đọc `Script`, không biết nội tạng pipeline, để baseline được chấm bằng đúng bộ metric đó.

Prompt luôn là file Jinja2 trong `prompts/`, không viết prompt trong file `.py`, vì người không code (PM) cũng cần sửa được prompt và style pack.

## Thứ tự xây dựng

Mục tiêu là nhánh `main` lúc nào cũng chạy được từ đầu đến cuối. Lỗi hay gặp nhất ở hackathon là tới ngày cuối mới ghép các module lần đầu.

1. `schemas.py` (xem `references/schemas.md`), rồi `fixtures/script_sample.json` viết tay và hợp lệ với schema.
2. `llm.py` với `LLMProvider`, `FakeLLMProvider`, cache đĩa theo hash, log usage ra JSONL.
3. `engine.py` gọi các hàm còn rỗng; `test_engine_fake.py` xanh.
4. Lấp ruột từng module: `plan.py` → `generate.py` → `guard.py` → `style.py`. `extract.py`, `app.py` và `eval/` làm song song được nhờ fixture.
5. `eval/run_eval.py` với baseline một prompt, chạy từ ngày 1 dù pipeline còn thô.

Sau mỗi bước, chạy `pytest` và `ruff check`. Thay đổi prompt thì chạy lại eval nhỏ và ghi kết quả vào PR.

## Plan: trọng số → ngân sách → điểm dạy → mức sâu

Phần này là code thuần, tất định, phải có unit test.

```python
w = a*w_teacher + b*w_quiz + c*w_user          # mặc định 0.4 / 0.4 / 0.2
w = w ** focus; w /= w.sum()                   # focus=1.5, làm sắc trọng tâm
w = np.maximum(w, w_min * prereq); w /= w.sum()  # sàn 0.05 cho chương tiên quyết
words  = w * minutes * wpm * 0.88              # 12% cho mở bài và tóm tắt
points = np.rint(words / words_per_point)      # ~170 từ cho một điểm dạy tử tế
depth  = "deep" nếu points>=2, "core" nếu ==1, ngược lại "bridge"
```

- `w_quiz = 1 − tỉ lệ đúng`, chỉ dùng khi chương có ít nhất 3 câu hỏi; thiếu thì bỏ nguồn này và chuẩn hoá lại hệ số.
- `wpm` mặc định 140 nhưng là tham số trong `config.py`, vì tốc độ đọc tiếng Việt cần đo lại.
- Trọng số toàn 0 hoặc âm: báo lỗi rõ ràng, không đoán.
- Test tối thiểu: tổng bằng 1; sàn tiên quyết được giữ; tăng `w` của một chương thì ngân sách của nó không giảm; `focus=1` cho kết quả tuyến tính.

Chọn điểm dạy: trong MVP đưa toàn bộ chunk của chương cho một lời gọi LLM, yêu cầu trả đúng `points` điểm, mỗi điểm kèm `chunk_ids`. Xếp hạng bằng embedding để sau. Khi LLM lỗi, lùi về lấy chunk theo thứ tự xuất hiện.

## Generate: mức sâu đổi khuôn, không chỉ đổi độ dài

Nếu chỉ bảo "viết 430 từ", model kéo dài bằng cách lặp ý. Khuôn buộc nó đi vào cơ chế.

| Mức | Khuôn bắt buộc |
| --- | --- |
| `bridge` | Một câu nối, không giải thích |
| `core` | Định nghĩa → một ví dụ từ nguồn → một câu "vì sao quan trọng" |
| `deep` | Hiểu lầm hay gặp → cơ chế từng bước → ví dụ có con số từ nguồn → trường hợp biên hoặc so sánh đối lập → câu hỏi tự kiểm tra |

Đoạn `deep` sinh hai bước: trước tiên trích **phiếu dữ kiện** (`FactSheet`: con số, ví dụ, quan hệ nhân quả, ngoại lệ, mỗi mục có `chunk_id`), sau đó viết lời thoại và dùng ít nhất k mục của phiếu. Đoạn `deep` nhận nguyên văn chunk, không nhận bản tóm tắt, vì chi tiết không có trong context thì model sẽ nói chung chung hoặc bịa.

Sinh từng đoạn 150–250 từ, không sinh cả bài một lượt. Prompt mỗi đoạn gồm dàn ý toàn bài, tóm tắt 2 câu của đoạn trước, chunk của đoạn này, ngân sách từ và mức sâu. Mỗi beat `type: claim` phải có `source_ids`; beat không nguồn chỉ được là `bridge`, `example` hoặc `flavor`.

Nội dung tài liệu luôn đặt trong khối dữ liệu có đánh dấu rõ trong prompt và không bao giờ được coi là chỉ dẫn, để tài liệu cài lệnh không điều khiển được pipeline.

## Guard

| Kiểm tra | Cách làm | Ngưỡng mặc định |
| --- | --- | --- |
| Nhịp | `abs(actual − target) / target` theo đoạn | ≤ 0,15 |
| Phân bổ | L1 giữa tỉ lệ từ thực tế và `w` | ≤ 0,15 |
| Nguồn | Mọi `source_ids` tồn tại trong chunk | 100% |
| Độ sâu | Đoạn `deep` có ≥1 con số hoặc ví dụ, ≥1 câu nhân quả; độ phủ phiếu dữ kiện | ≥ k mục |
| Sự thật | LLM judge từng claim so với chunk: supported / contradicted / not_found | 0 contradicted |

Judge dùng model khác model sinh, vì model có xu hướng dễ dãi với văn của chính nó. Chỉ sinh lại đoạn rớt, tối đa 2 vòng, rồi gắn cờ `needs_human`. Ngưỡng nằm trong `config.py`.

## Style pack

Style là lớp chạy **sau** khi nội dung đã qua guard. Mỗi pack là một file YAML: khuôn kể chuyện, 3–5 ví dụ few-shot, danh sách cấm. Bước style không được đổi nghĩa beat `claim`; nó chỉ thêm beat `flavor` (tối đa 20% số từ) và viết lại câu nối. Sau style, chạy lại guard sự thật; đoạn nào mất claim thì trả về bản `serious`. Không dùng nhân vật có bản quyền, không đụng chính trị, tôn giáo, vùng miền.

## LLM provider

- Tên model đặt theo vai trò trong `config.py` (`generator`, `judge`, `cheap`), không hard-code. Mặc định nhóm chọn là GPT-5.6 Luna qua API OpenAI; vì tên model và giá đổi nhanh, hãy kiểm tra tài liệu hiện hành thay vì tin trí nhớ.
- Output có cấu trúc: yêu cầu model trả JSON theo schema Pydantic và validate; lỗi parse thì thử lại một lần rồi lùi về phương án code.
- Cache theo hash của (prompt đã render, model, tên schema). Sửa prompt của bước sau không phải trả tiền lại cho bước trước.
- Log mỗi lời gọi: bước, model, token vào, token ra, chi phí, thời gian. Lấy số token từ trường usage của response, không ước lượng. Token suy luận bị tính như token ra, nên đặt mức reasoning theo bước: thấp cho câu nối và style, cao hơn cho judge.
- Khoá API chỉ đọc từ biến môi trường; không commit `.env`.

## Eval

Không có benchmark công khai nào khớp bài toán này, và ROUGE với nguồn thưởng cho việc chép nguyên văn, nên nhóm tự làm mini-benchmark. Chi tiết metric và cách chấm ở `references/eval.md`; đọc file đó khi viết `eval/`.

Tóm tắt: 5 tài liệu × 2 cấu hình trọng số, so với baseline một prompt và một ablation tắt trọng số. Sáu metric tự động (độ lệch phân bổ, độ phủ chunk, claim có nguồn đúng, mật độ cụ thể, tỉ lệ chép nguyên văn, claim mất sau style), phép thử câu hỏi "vì sao", chi phí và thời gian mỗi kịch bản. Báo kết quả trung thực kể cả khi xấu; không điền số chưa đo.

## Cách làm việc với người dùng

- Trả lời và viết comment, docstring bằng tiếng Việt; tên biến, hàm, file bằng tiếng Anh.
- Trước khi thêm dependency hoặc framework mới, nêu lý do. Mặc định không dùng LangChain hay LangGraph: pipeline tuyến tính với một vòng lặp nhỏ, Python thuần dễ debug hơn. Tránh PyMuPDF nếu hướng tới product đóng (giấy phép AGPL); dùng `pypdf` hoặc `docling`.
- Thay đổi `schemas.py` ảnh hưởng cả nhóm: đề xuất thay đổi, giải thích tác động lên fixture và các module, rồi mới sửa.
- Khi được giao một module, viết test trước cho phần code thuần, rồi tới phần có LLM với `FakeLLMProvider`.
