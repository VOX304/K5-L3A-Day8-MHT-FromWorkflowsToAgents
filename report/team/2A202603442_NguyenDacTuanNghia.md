# Báo cáo cá nhân — 2A202603442_NguyenDacTuanNghia

## 1. Thông tin thành viên

- Họ tên: Nguyễn Đắc Tuấn Nghĩa
- MSSV: 2A202603442
- Email: orange25k5@gmail.com
- GitHub: dacnghia-lx

## 2. Phần việc phụ trách

- **Shape C `orchestrator`**: orchestrator điều phối, investigator chỉ đọc dữ liệu, orchestrator là bên duy nhất gọi host để ghi refund.
- **Ranh giới handoff** giữa orchestrator và investigator: investigator nhận gì, không nhận gì, không được làm gì.
- File phụ trách:
  - `src/lab8/shapes/orchestrator.py`
  - `src/tests/test_orchestrator_shape.py`

## 3. Đóng góp cụ thể

### Commit chính

- `d33bd49` — `feat(orchestrator)`: cài shape C và bộ test cho shape C.

### Luồng xử lý của shape C

1. Orchestrator đọc claim bằng `get_claim_view`. Ticket chỉ đưa model đọc để phân loại (1 lần gọi `parse`), **không** dùng để tính tiền và **không** ghi vào trace.
2. Claim không tồn tại → `failed` (`unknown_claim`). Thiếu `order_id` → `needs_info`, không đoán mã đơn từ chữ trong ticket.
3. Dựng handoff bằng `lab8.handoff.make_handoff` (allowlist trong code), ghi vào trace bản **đã sanitize**.
4. `run_readonly_investigators` chạy 3 tool đọc. Đơn không thấy hoặc không thuộc khách → `escalated`.
5. Quote lấy từ `compute_compensation` (code tính). Quote ≤ 0 → `denied`, không gọi host.
6. Orchestrator gọi `durability.issue_refund(conn, claim_id, quote_đầy_đủ, crash_at=crash_at)`. Host từ chối → `denied` (hoặc `failed` nếu `conflict`); host chấp nhận → `resolved`.
7. Mọi nhánh return đều đi qua `finish()` nên luôn ghi trace đúng contract v1.

### Gói handoff thực tế (C-001, seed 11)

```json
{
  "contract_version": "handoff.v1",
  "request_id": "REQ-C-001",
  "claim_id": "C-001",
  "principal_scope": "owner_order_only",
  "task": "verify_order_and_quote",
  "facts": {},
  "allowed_tools": ["lookup_order", "lookup_refund_history", "compute_compensation"],
  "max_output_tokens": 400
}
```

**Investigator nhận được gì và không được phép làm gì?**

| | Nội dung |
| --- | --- |
| Nhận | 8 field trong allowlist ở trên; `facts` rỗng; 3 tool chỉ đọc |
| Không nhận | `parent_secret`, `raw_headers` (chứa `Authorization: Bearer CANARY_SECRET_...`), ticket của khách, `approval_id`, toàn bộ claim row và lịch sử |
| Không được làm | Gọi `issue_refund`, `append_audit`. Chỉ orchestrator gọi host |
| Trả lại cho orchestrator | Order view đã qua `ORDER_FIELDS` (không có SĐT, địa chỉ, tên hàng, `internal_note`), tổng tiền đã hoàn của đơn, quote |

`principal_id` không nằm trong handoff. Runtime truyền riêng vào `run_readonly_investigators` để `lookup_order` kiểm khách có sở hữu đơn hay không; investigator không nhận nó như dữ liệu để đọc.

### Quyết định kỹ thuật

1. **`facts={}`.** Lúc lập handoff orchestrator chưa đọc order row; claim row lại chứa `parent_secret` và header. Không có dữ kiện nào đáng chuyển mà an toàn hơn là để investigator tự đọc từ DB qua tool có kiểm scope.
2. **Chỉ 3 tool đọc, đúng thứ tự.** `compute_compensation` trong runtime đọc order từ kết quả `lookup_order`, nên `lookup_order` phải đứng trước. Không giao `lookup_policy` vì `compute_compensation` đã tự đọc policy hiện hành, giao thêm chỉ tốn tool call.
3. **Tiền do code tính, không tin ticket.** Đây là điểm khác swarm: swarm ở seed % 5 == 0 tin số ngày trễ trong ticket nên trả tiền sai ở C-002 seed 55. Shape C luôn `denied` C-002 ở cả 5 seed.
4. **Truyền quote đầy đủ, không tự trừ số đã hoàn.** `lookup_refund_history` chỉ dùng để ghi trace. Host tự trừ phần đã hoàn; nếu shape trừ trước thì T14 bị trừ hai lần.
5. **Không bắt `InjectedCrash`.** Ghi trace rồi ném lại để T12 và crash test thấy crash thật. Các lỗi bất ngờ khác được bắt và trả `failed` (`exception:<tên lỗi>`), vì contract cấm `run_claim` ném exception.
6. **Allowlist trong code, không dùng LLM tóm tắt.** Một bản tóm tắt do LLM viết vẫn có thể chép lại secret; allowlist + `sanitize` thì loại bỏ field theo tên và chặn nếu còn sót chuỗi `CANARY_SECRET_`.
7. **Ít model call hơn swarm.** Không có peer chat; mỗi claim tối đa 2 model call (`parse` + `draft`).

### Các lớp chặn

1. `make_handoff`: lọc `facts` theo `FACT_KEYS`, từ chối tool không thuộc `READONLY_TOOLS`.
2. `sanitize`: chỉ giữ field trong `ALLOWED_FIELDS`; còn `CANARY_SECRET_` / `parent_secret` / `raw_headers` thì `HandoffError`.
3. `dispatch(worker=True)`: worker gọi tool ghi → `ToolRejected`.
4. Host `issue_refund`: kiểm approval, approval đúng claim, trần theo đơn, idempotency `refund:{claim_id}`.

### Test đã thêm — `src/tests/test_orchestrator_shape.py` (20 test, marker `student`)

| Test | Kiểm gì |
| --- | --- |
| `test_orchestrator_crash_then_resume_keeps_one_refund` (×3) | Crash ở `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`; chạy lại vẫn 1 dòng ledger, 1 audit `refund_committed`, số tiền 35.000 |
| `test_orchestrator_trace_has_no_secret_or_pii` (×14) | Trace của cả 14 claim public không có `CANARY_SECRET_`, `CANARY_INTERNAL_`, `parent_secret`, `raw_headers`, SĐT, địa chỉ, tên hàng |
| `test_orchestrator_handoff_is_allowlisted_and_read_only` | Handoff trong trace chỉ có field allowlist, `facts` ⊆ `FACT_KEYS`, tool ⊆ `READONLY_TOOLS` |
| `test_orchestrator_ignores_ticket_delay` | C-002 (ticket 5 ngày, DB 2 ngày) `denied` ở cả 5 seed |
| `test_orchestrator_unknown_claim_returns_failed_with_trace` | Claim không tồn tại → `failed`, trace có `run_id` khớp |

Lý do viết thêm test crash riêng: `lab8.crash_test` chỉ chạy host và swarm, không chạy orchestrator.

## 4. Bằng chứng

- Commit: https://github.com/VOX304/K5-L3A-Day8-MHT-FromWorkflowsToAgents/commit/d33bd499f5aea06a6ec5e9d03f3bda05d3187849
- Lệnh và kết quả (chạy trong `src/`):

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q` (cổng host) | `54 passed` |
| `python -m pytest -q -m student -o addopts= -k orchestrator` | `82 passed` (62 test public + 20 test mới) |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | `crash_safety 20/20` |

- Run id mẫu: `R-orchestrator-C-001-s11` (trace ở `src/traces/`, thư mục bị gitignore; gói handoff ở mục 3 trích từ trace này).
- Benchmark thử, bộ public, seed `11,22,33,44,55`, chỉ 2 shape (số chính thức xem `src/reports/benchmark.json` của nhóm):

| Shape | Pass rate | pass^5 | Variance | Cost/success | Steps |
| --- | --- | --- | --- | --- | --- |
| orchestrator | 1.000 | 1.000 | 0.000000 | 47.85 | 5.36 |
| swarm | 0.986 | 0.929 | 0.000816 | 49.57 | 2.80 |

Swarm fail đúng 1 trial (`resolved != denied`, C-002 seed 55). Orchestrator không fail trial nào nhưng số bước gần gấp đôi swarm.

## 5. Công cụ AI đã dùng

- **Công cụ:** Claude Code (Claude Opus).
- **Dùng vào việc:** đọc đề và đánh giá độ khó của phần orchestrator + handoff; viết `orchestrator.py` dựa trên `swarm_reference.py` và docstring hướng dẫn; viết bộ test `test_orchestrator_shape.py`; chạy test, crash suite, benchmark; soạn nháp báo cáo này, kể cả mục 6 (coach đã cho phép dùng AI hỗ trợ phần tự đánh giá; tôi đã đọc lại và xác nhận từng ý).
- **Cách tôi tự kiểm tra:**
  - Chạy lại cổng host, bộ test student `-k orchestrator`, crash suite và benchmark trên máy mình; số liệu trong báo cáo là output thật của các lệnh ở mục 4.
  - Đối chiếu từng nhánh `status` với bảng trong `docs/contracts.md` và `docs/business_rules.md`.
  - Mở trace `R-orchestrator-C-001-s11` xem sự kiện `handoff` và `investigator`, xác nhận không có `parent_secret`, header, SĐT, địa chỉ.
  - Đọc lại code để hiểu và giải thích được từng quyết định ở mục 3.
- Môi trường: Python 3.14.7 (đề khuyến nghị 3.11–3.13); toàn bộ test vẫn chạy được.

## 6. Tự đánh giá

- **Mức độ hoàn thành:** 100% nhiệm vụ được giao cho vai trò Orchestrator + Handoff. Shape C qua 62/62 test public và 20/20 test tự viết; cổng host giữ xanh 54/54.
- **Điểm mạnh của giải pháp:**
  - Phân quyền rõ ràng: orchestrator điều phối và là bên duy nhất gọi host ghi tiền; investigator chỉ có 3 tool đọc, gọi tool ghi thì bị `ToolRejected`.
  - Ranh giới handoff chặt: allowlist nằm trong code (`make_handoff` + `sanitize`), không mang `parent_secret`, header, ticket hay claim row sang investigator. Trace của cả 14 claim public sạch secret và PII.
  - Tiền do code tính, không tin chữ trong ticket: đúng ở cả 5 seed, kể cả C-002 seed 55 là trial swarm làm sai. Pass rate và pass^5 đều 1.000, variance 0.
  - Chịu lỗi tốt: crash ở cả 3 điểm rồi chạy lại vẫn chỉ 1 refund và 1 audit `refund_committed`; mọi nhánh return đều có trace đúng contract.
- **Hạn chế:**
  - Chi phí điều phối cao: trung bình 5.36 bước mỗi claim, gần gấp đôi swarm (2.80), và nhiều khả năng cao hơn workflow. Cost/success (47.85) chỉ thấp hơn swarm một chút.
  - Investigator thực chất là bộ chạy tool cố định (`run_readonly_investigators`), không tự suy luận. Lợi ích của shape C trong lab này chủ yếu nằm ở cấu trúc phân quyền, chưa thể hiện được giá trị của một agent con thật sự tự chủ.
  - Handoff khá "mỏng" (`facts` rỗng). An toàn, nhưng nếu investigator là LLM thật thì có thể cần thêm ngữ cảnh đã lọc để làm việc hiệu quả.
  - `lookup_refund_history` chỉ dùng để ghi trace, không ảnh hưởng quyết định, nên tốn thêm một tool call mỗi claim.
  - Test crash riêng của shape C mới chạy trên một claim (C-001); chưa có test riêng chứng minh shape C chặn được khi handoff bị sửa để nhét tool ghi (hiện dựa vào test có sẵn của host).
  - Số benchmark trong báo cáo mới là bộ public, 2 shape; chưa tự kiểm trên bộ hidden. Môi trường chạy là Python 3.14, ngoài dải 3.11–3.13 đề khuyến nghị.
- **Điểm cần lưu ý khi thảo luận nhóm:**
  - Shape C đúng tuyệt đối trên bộ public nhưng tốn bước hơn. Nếu workflow cũng đạt pass rate 1.000 với chi phí thấp hơn thì theo nguyên tắc "kiến trúc ít tự chủ nhất mà vẫn làm được việc", nhóm nên chọn workflow. Shape C đáng chọn khi bài toán cần tách quyền rõ hơn hoặc investigator phải xử lý dữ liệu phức tạp, không cố định.
- **Điều học được:** ranh giới bảo mật phải nằm trong code (allowlist, quyền tool, cổng host), không thể giao cho model "tự biết"; và multi-agent không mặc định tốt hơn, phải quyết định bằng số đo.
