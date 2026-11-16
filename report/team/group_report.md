# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: MHT
- Thành viên: xem `TEAM.md` (Nguyễn Đắc Tuấn Nghĩa, Vũ Mạnh Hoạch, Nguyễn Văn Tùng, Võ Công Minh)
- Commit chốt (trùng `report/team/decision_adr.md`): 06279a5

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc có cùng chữ ký `run_claim`, rồi chọn kiến trúc ít tự chủ nhất mà vẫn làm được việc dựa trên số đo. Nhóm thống nhất từ đầu ba nguyên tắc lấy từ `docs/business_rules.md` và `docs/contracts.md`: (1) số tiền do `compute_compensation` tính từ order row, không do model và không do chữ trong ticket; (2) mọi thao tác ghi tiền đi qua `durability.issue_refund` với **quote đầy đủ**, để host tự kiểm approval, trần theo đơn và idempotency; (3) trace là ranh giới bảo mật, chỉ ghi field đã qua allowlist.

Chia việc theo gợi ý nhóm 4 người:

| Thành viên | Vai | Phần chính |
| --- | --- | --- |
| Vũ Mạnh Hoạch | Workflow + integration | Shape A, chạy kiểm thử tích hợp |
| Nguyễn Văn Tùng | Single agent | Shape B (ReAct tối đa 8 bước) |
| Nguyễn Đắc Tuấn Nghĩa | Orchestrator + handoff | Shape C, ranh giới handoff |
| Võ Công Minh | Ledger + evaluation | Test an toàn, crash, benchmark, ablation |

Thứ tự làm: đọc swarm tham chiếu (shape D) để nắm khung → ba shape A, B, C làm song song trên ba nhánh riêng → gộp vào nhánh evaluation để đo chung → merge cả bốn nhánh vào `main`.

## 3. Giải pháp

Ranh giới chung cho cả ba shape: model (MockLLM) chỉ đọc và soạn chữ; code quyết định status, số tiền và có gọi host hay không. Không shape nào ghi thẳng vào database.

**Shape A — workflow** (`src/lab8/shapes/workflow.py`). Chuỗi bước Python cố định, không gọi model: `get_claim_view` → thiếu `order_id` thì `needs_info` → `lookup_order` (không thấy hoặc sai chủ thì `escalated`) → `compute_compensation` từ order row (quote ≤ 0 thì `denied`) → `lookup_refund_history` để ghi trace, không trừ vào quote → `issue_refund(quote đầy đủ, crash_at)`. Trace: `quote`, `refund_history`, `host_call`, `host_result`, `final`; trace được ghi xuống đĩa trước khi gọi host để vẫn hợp lệ nếu crash.

**Shape B — single agent** (`src/lab8/shapes/single.py`). Vòng `run_react` tối đa 8 bước, chạy với `worker=True` nên runtime chặn mọi tool ngoài `READONLY_TOOLS`. Hàm `decide` chọn lần lượt `get_claim_view`, `lookup_order`, `compute_compensation`, `lookup_refund_history`, có gọi MockLLM (`parse`, `decide`) nhưng không để model quyết định số tiền. Sau vòng lặp, code của shape gọi `issue_refund`. Trace: `agent_step`, `observation` (chỉ ghi cờ `found`/`visible` và số tiền, không ghi row), `host_call`, `host_result`.

**Shape C — orchestrator** (`src/lab8/shapes/orchestrator.py`). Orchestrator đọc claim, gọi model một lần để phân loại ticket rồi dựng handoff bằng `make_handoff`:

```json
{"contract_version": "handoff.v1", "request_id": "REQ-C-001", "claim_id": "C-001",
 "principal_scope": "owner_order_only", "task": "verify_order_and_quote", "facts": {},
 "allowed_tools": ["lookup_order", "lookup_refund_history", "compute_compensation"],
 "max_output_tokens": 400}
```

Investigator (`run_readonly_investigators`) chỉ có 3 tool đọc; gọi tool ghi thì bị `ToolRejected`. Handoff **không** mang `parent_secret`, `raw_headers`, ticket, `approval_id` hay claim row: `sanitize` chỉ giữ 8 field allowlist và từ chối nếu còn chuỗi `CANARY_SECRET_`. `principal_id` được runtime truyền riêng để kiểm quyền sở hữu đơn, không nằm trong handoff. Orchestrator là bên duy nhất gọi `issue_refund`. Trace: `orchestrator`, `handoff` (bản đã sanitize), `investigator` (order view đã lọc + `refunded_vnd`), `quote`, `host`, `decision`. Nhóm không dùng LLM tóm tắt thay cho allowlist, vì bản tóm tắt vẫn có thể chép lại secret.

Cả ba shape: truyền `crash_at` vào host và không bắt `InjectedCrash`; mọi nhánh return đi qua `finish()` nên luôn có trace đúng contract v1.

## 4. Kết quả

Bộ public, `src/reports/benchmark.json`: 280 trial = 4 shape × 14 claim × seed 11, 22, 33, 44, 55; cùng MockLLM, world, bảng giá, evaluator, database SQLite mới cho mỗi trial.

| Shape | Đúng/trial | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Model call TB |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| workflow | 70/70 | 1.000 | 1.000 | 1.000–1.000 | 0 | 34.29 | 3.79 / 5 | 0 |
| single | 70/70 | 1.000 | 1.000 | 1.000–1.000 | 0 | 36.45 | 9.79 / 12 | 4.43 |
| orchestrator | 70/70 | 1.000 | 1.000 | 1.000–1.000 | 0 | 47.85 | 5.36 / 6 | 2.00 |
| swarm | 69/70 | 0.986 | 0.929 | 0.929–1.000 | 0.0008 | 49.57 | 2.80 / 3 | 3.00 |

Swarm sai đúng một trial, `R-swarm-C-002-s55`: tin ticket "trễ 5 ngày" thay vì order row 2 ngày nên trả `resolved` thay vì `denied`. Đây là điểm yếu cố ý của bản tham chiếu. Ba shape nhóm viết đều `denied` C-002 ở cả 5 seed. Steps là số event trace, nên single có mean steps lớn hơn 8 vẫn không vượt giới hạn 8 vòng ReAct.

An toàn và durability:

- Crash suite chính thức `src/reports/crash.json`: **20/20**. Suite này chủ yếu kiểm host và một ca swarm, nên nhóm bổ sung 9 ca crash end-to-end (3 cửa sổ crash × 3 shape) trong `src/tests/test_evaluation_safety.py` và 3 ca crash riêng cho orchestrator trong `src/tests/test_orchestrator_shape.py`. Tất cả đều chỉ ra một refund và một audit `refund_committed`.
- Approval: 15 ca approval thiếu, không tìm thấy, hết hạn, thu hồi, sai claim đều `denied`, không có refund, có `policy_denied` đúng lý do.
- Secret/PII: trace của cả 14 claim (orchestrator) và stdout/stderr/artifact của ca C-010 (ba shape) không chứa canary, header hay giá trị PII.
- Tổng test (`python -m pytest -q -o addopts=`): 364 passed ở commit đo `e27e680` (`src/reports/evaluation_tests.xml`); 367 passed ở commit chốt `06279a5` sau khi merge thêm test của single agent.
- Hidden: chưa có `student_drop/` trong workspace nên chưa tự kiểm; pass rate hidden do giảng viên chấm.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md` (chọn **workflow**). Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`. Ablation bỏ `lookup_refund_history` khỏi investigator giữ nguyên 70/70 và giảm cost/success của orchestrator từ 47.85 xuống 38.57 VND (`src/reports/ablation_history.json`).

## 5. Khó khăn và cách xử lý

| Khó khăn | Cách xử lý |
| --- | --- |
| Trần hoàn tiền theo đơn (T13, T14): dễ tự trừ số đã hoàn trước khi gọi host, khiến host trừ lần hai và T14 sai | Cả ba shape truyền quote đầy đủ; `lookup_refund_history` chỉ dùng để ghi trace |
| Crash test: bọc `try/except` quá rộng sẽ nuốt `InjectedCrash`, T12 báo "crash did not fire" | Bắt `InjectedCrash` riêng, ghi trace rồi `raise` lại; các lỗi khác mới trả `failed` vì contract cấm `run_claim` ném exception |
| Nguy cơ lộ secret qua trace: claim row có `parent_secret`, order row có SĐT/địa chỉ | Chỉ ghi field đã qua `get_claim_view`/`lookup_order`/handoff allowlist; viết test quét trace tìm canary và PII |
| Crash suite chính thức không chạy ba shape của nhóm | Viết thêm test crash end-to-end cho từng shape thay vì coi 20/20 của host là đủ |
| Merge bốn nhánh vào `main`: `git merge` bị chặn vì `src/reports/crash.json` local chưa track; conflict ở `TEAM.md` (nhánh single và nhánh evaluation sửa cùng bảng) và ở `orchestrator.py` (chỉ khác ký tự xuống dòng cuối file) | Xóa file report local, dùng bản của nhánh evaluation; gộp `TEAM.md` giữ bảng thành viên đầy đủ và bảng đóng góp đủ 4 dòng; giữ bản orchestrator gốc bằng `git checkout --ours`; chạy lại 82 test orchestrator sau merge |
| `check_submission` sau merge còn 7 FAIL, đều do `decision_adr.md` chưa điền | Điền ADR bằng số từ `src/reports/benchmark.json` và `crash.json`, có run id |
| Môi trường một máy chỉ có Python 3.14 (đề khuyến nghị 3.11–3.13) | Tạo venv với 3.14; smoke, host test, student test đều chạy được |

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`:

- `report/team/2A202603442_NguyenDacTuanNghia.md`
- `report/team/2A202603500_VuManhHoach.md`
- `report/team/2A202603471_NguyenVanTung.md`
- `report/team/2A202503520_VoCongMinh.md`

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`; giá là mô phỏng, không phải hóa đơn API.

- Bộ public chỉ có 14 claim và cả ba shape đều đạt 1.000, nên benchmark không phân biệt được độ đúng giữa chúng; quyết định dựa vào cost và mức tự chủ.
- So sánh là giữa các bản triển khai hoàn chỉnh, không cô lập nhân quả của topology: số model call, prompt và cách ghi trace mỗi shape khác nhau.
- Investigator của orchestrator là bộ chạy tool cố định, không tự suy luận, nên chưa thể hiện được giá trị của một agent con thật sự.
- Chưa tự kiểm trên bộ hidden.

Điều kiện làm kết luận thay đổi: với model thật, single/orchestrator có thể dao động theo seed còn workflow thì không, nên lợi thế của workflow có thể còn lớn hơn. Ngược lại, nếu bộ hidden có claim cần đọc dữ liệu phi cấu trúc hoặc chọn tool theo tình huống mà luồng cố định không bao được, khiến workflow rơi dưới 0.75, nhóm sẽ cân nhắc chuyển sang single.

## 8. Tài liệu tham khảo

- Đề bài và tài liệu lab: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
- Kim et al., *Towards a Science of Scaling Agent Systems*, arXiv v3 (08/04/2026), https://arxiv.org/abs/2512.08296v3 (nguồn của research card, R1).
- Báo cáo evaluation nội bộ: `docs/cp4-cp5-evaluation.md`.
- Số liệu: `src/reports/benchmark.json`, `src/reports/crash.json`, `src/reports/ablation_history.json`, `src/reports/evaluation_tests.xml`.
