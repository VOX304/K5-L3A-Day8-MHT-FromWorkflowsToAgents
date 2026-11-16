# CP4–CP5: kết quả ledger và evaluation đến Ticket 05

## Phạm vi và phiên bản đo

- Nhóm MHT; phụ trách ledger + evaluation: Võ Công Minh (2A202503520).
- Phiên bản code dùng đo: `e27e680` (commit tích hợp workflow/single người dùng cung cấp, giữ orchestrator đã merge từ Nghĩa, thêm test và biến thể thí nghiệm).
- Mốc trước đợt này: `238b6cd`. Không thay đổi host, policy, durability, metrics, config hoặc dữ liệu public.
- Thao tác thực thi và soạn tài liệu có trợ lý Codex hỗ trợ; không giả lập đóng góp hay mức tự đánh giá cá nhân của các thành viên.
- Baseline trước test bổ sung: 322 passed. Sau 42 test mới: 364 passed, không fail/error; bằng chứng máy đọc tại `src/reports/evaluation_tests.xml`.

## Ticket 02 — bằng chứng an toàn CP4

`src/tests/test_evaluation_safety.py` có 33 ca end-to-end cho workflow, single và orchestrator:

| Nhóm ca | Số ca | Điều quan sát |
| --- | ---: | --- |
| Approval thiếu, không tìm thấy, hết hạn, thu hồi, sai claim | 15 | Denied, full quote giữ 35.000, không refund/audit committed, có policy_denied đúng lý do |
| Ba cửa sổ crash × ba shape | 9 | Crash thật sự xảy ra; resume và retry lần nữa vẫn một refund 35.000, một audit committed |
| Hai claim khác nhau trên cùng đơn | 3 | Claim thứ hai denied, tổng hoàn của đơn không tăng |
| Approval đổi hạn mức sau khi đã commit | 3 | Retry báo amount_conflict, giữ nguyên khoản 35.000 và audit cũ |
| Stdout/stderr và artifact của ca C-010 | 3 | Không chứa canary/secret/header hay các giá trị PII từ fixture |

Mỗi ca dùng database tạm mới; chỉ sửa input trong database tạm để dựng tình huống.
Đối chiếu qua run_claim, RunResult và contract ledger/audit SQLite, không mock hàm nội bộ.
Các test public hiện có tiếp tục kiểm trace và các case T01–T14.

Crash suite chính thức tạo `src/reports/crash.json`: **20/20**.
Suite này chủ yếu kiểm host và một ca swarm; 9 ca crash end-to-end bổ sung mới kiểm đủ ba shape nhóm viết.
Không đồng nhất 20/20 của host với việc mọi shape đã được kiểm crash.
Không phát hiện approval bypass/secret leak trong những ca đã kiểm; chưa có kết quả hidden.

## Ticket 03 — benchmark public

Báo cáo gốc: `src/reports/benchmark.json`, **280 trial = 4 shape × 14 claim × 5 seed**.
Seed 11, 22, 33, 44, 55; as_of cố định 2026-11-15; cùng MockLLM, dữ liệu, registry tool, bảng giá, evaluator; mỗi trial một database SQLite mới.

| Shape | Đúng/trial | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean/p95 steps |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| workflow | 70/70 | 1,000000 | 1,000000 | 1–1 | 0 | 34,285714 | 3,785714 / 5 |
| single | 70/70 | 1,000000 | 1,000000 | 1–1 | 0 | 36,450000 | 9,785714 / 12 |
| orchestrator | 70/70 | 1,000000 | 1,000000 | 1–1 | 0 | 47,852857 | 5,357143 / 6 |
| swarm | 69/70 | 0,985714 | 0,928571 | 0,928571–1 | 0,0008163265 | 49,566957 | 2,8 / 3 |

Swarm sai đúng một trial: `R-swarm-C-002-s55`, trả resolved thay vì denied do lấy số ngày trong ticket thay dữ liệu đơn. Đây là điểm yếu cố ý của bản tham chiếu, không phải lỗi cần sửa trong thước đo.

Pass rate đếm từng trial; pass^5 yêu cầu claim đúng ở cả năm seed. Vì vậy một trial sai làm swarm mất một claim ở pass^5.
Cost/success tính cả chi phí của trial fail. Giá hoàn toàn mô phỏng, không phải hóa đơn API; latency là unavailable.

Workflow có cost/success thấp nhất trong bốn bản đang đo, trong khi ba shape nhóm đều đạt 70/70 public.
Đây là dữ liệu cung cấp cho Ticket 06; chưa tự điền quyết định kiến trúc vào ADR thay nhóm.
Kết quả so sánh các bản triển khai hoàn chỉnh, không cô lập nhân quả của topology: số model call, prompt và cách ghi trace của các shape khác nhau.
Steps là số event trace; single có mean steps lớn hơn 8 vẫn không vi phạm giới hạn 8 vòng ReAct. Swarm ghi ít event không chứng minh nó ít công việc hơn.

## Ticket 04 — ablation một biến

Nguồn primary đã kiểm: Kim et al., [Towards a Science of Scaling Agent Systems, v3](https://arxiv.org/abs/2512.08296v3), cập nhật 08/04/2026.
Nguồn dùng đánh giá kiểm soát để tách ảnh hưởng kiến trúc và quan sát overhead trên tác vụ dùng nhiều tool. Lab chỉ dùng ý tưởng kiểm soát một yếu tố; không tái lập định luật scaling của paper.

Giả thuyết được ghi trong research card ở commit e27e680 trước khi đo: bỏ bước lookup_refund_history khỏi kế hoạch investigator không đổi quyết định tiền vì host luôn kiểm lịch sử trong transaction, nhưng giảm chi phí đọc.
Biến thể `bonus.orchestrator_no_history` nạp bản orchestrator vào module độc lập, chỉ bỏ một bước đọc; đổi nhãn shape để trace không đè baseline. Không thay đổi registry tool, quyền host, model, prompt, seed, world, corpus, giá hoặc evaluator.

| Chỉ số | Baseline | Không đọc history ở investigator |
| --- | ---: | ---: |
| Trial đúng | 70/70 | 70/70 |
| Pass rate / pass^5 | 1 / 1 | 1 / 1 |
| Tổng model calls | 140 | 140 |
| Tổng cost mô phỏng | 3.349,70 | 2.699,70 |
| Cost/success | 47,852857 | 38,567143 |
| Mean/p95 trace steps | 5,357143 / 6 | 5,357143 / 6 |

Tiết kiệm **65 tool call, 650 VND mô phỏng (~19,40%)**. C-004 thiếu order_id nên không có handoff và không tiết kiệm call; 13 claim còn lại × 5 seed = 65.
So theo từng claim/seed: không khác passed/status/reason/model_calls. 70 row baseline trong ablation khớp baseline ở benchmark chính thức.
Test ablation có 9 ca, gồm đối chiếu quyết định tiền/token/model usage trên các nhánh chính và ba cửa sổ crash.
Giới hạn: trace mất giá trị refunded_vnd đã đọc trước; không chứng minh việc đọc lịch sử là thừa trong mọi thiết kế. Không thay bản orchestrator chính thức bằng biến thể.

## Ticket 05 — hidden self-check

Không có `src/student_drop/`, `hidden_claims.jsonl` hoặc `hidden_world_state.json` trong workspace khi kiểm tra.
Trạng thái **waiting-for-data**: chưa chạy hidden, không tạo hidden_selfcheck.json giả và không công bố pass rate hidden.
Khi giảng viên phát đủ dữ liệu, chạy lệnh dưới. Không nhãn thì chỉ kiểm tình trạng thực thi, trace và leak_suspect; điểm hidden chính thức do giảng viên chấm.

```powershell
.\.venv\Scripts\python.exe -m lab8.benchmark --shapes workflow,single,orchestrator --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json --seeds 11,22,33,44,55 --out reports/hidden_selfcheck.json
```

## Lệnh tái lập (chạy trong src, PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pytest -q -o addopts= --junitxml=reports/evaluation_tests.xml
.\.venv\Scripts\python.exe -m lab8.crash_test --count 20 --out reports/crash.json
.\.venv\Scripts\python.exe -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
.\.venv\Scripts\python.exe -m lab8.benchmark --shapes orchestrator,orchestrator_no_history --extra-shape orchestrator_no_history=bonus.orchestrator_no_history:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_history.json
.\.venv\Scripts\python.exe -m lab8.check_submission
```

Chạy tuần tự vì test/benchmark cùng ghi trace theo run_id; không chạy song song trên cùng thư mục trace.
Không sửa JSON bằng tay. Không commit trace, database, virtualenv, hidden data hoặc secret.

## Rà tài liệu và phần chưa hoàn tất

Đã đối chiếu CHECKPOINTS, RULES, RUBRIC, SUBMISSION, contracts, metrics, báo cáo cá nhân mẫu và research card.
Research card đã có nguồn, giả thuyết, phương pháp, kết quả thật. Báo cáo cá nhân Minh và một dòng đóng góp có test/commit thật đã được bổ sung.
ADR vẫn trống (Ticket 06), báo cáo/đóng góp của ba thành viên khác và báo cáo nhóm còn thuộc Ticket 07–08.
check_submission đã chạy sau cập nhật tài liệu: **7 FAIL**, đều là các trường ADR chưa điền; có WARN do còn thay đổi chưa commit tại lúc kiểm. Shape, benchmark, crash, research card và dòng đóng góp Minh đều được công cụ chấp nhận.
Chưa đạt trạng thái sẵn sàng nộp của Ticket 09; công cụ chấp nhận một dòng đóng góp cũng không có nghĩa đủ bằng chứng cho cả bốn người.
Nhóm cần phân biệt công cụ kiểm format này với điểm hidden. Không điền thông tin giả chỉ để đưa bộ kiểm về 0 FAIL.
