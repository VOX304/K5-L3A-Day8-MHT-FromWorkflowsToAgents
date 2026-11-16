# Cùng đi qua CP1–CP3

Các ticket nằm trong `.scratch/cp1-cp3/issues/`, mỗi file là một việc kiểm chứng được.
Thông tin thành viên không chặn triển khai code; phần contract của Ticket 02 phải hiểu trước khi viết shape.

## CP1: Biết mình đang giải bài toán gì

Ví dụ khách yêu cầu hoàn 35.000 đồng phí vận chuyển. Hệ thống cần biết đơn nào,
của ai, dữ liệu giao trễ thật, chính sách đang hiệu lực, approval và lịch sử hoàn.
Lời khách viết trong ticket có thể sai hoặc chứa câu yêu cầu bỏ qua chính sách.
Ta không dùng lời đó thay thế dữ liệu đơn hoặc cấp quyền ghi tiền.

| Từ | Hiểu trong bài này |
| --- | --- |
| Claim | Một yêu cầu xử lý của khách |
| Order | Đơn hàng gắn với yêu cầu |
| Quote | Mức tiền được hưởng đầy đủ theo chính sách |
| Approval | Phê duyệt do host gắn, có phạm vi và hạn mức riêng |
| Ledger | Sổ ghi khoản tiền thực sự đã hoàn |
| Trace | Nhật ký từng lần chạy, chỉ chứa dữ liệu được phép |

| Tình huống | Trạng thái | Điều cần nhớ |
| --- | --- | --- |
| Thiếu mã đơn | needs_info | Không lấy mã từ lời viết trong ticket |
| Không thấy đơn hoặc sai chủ | escalated | Không tiết lộ dữ liệu đơn |
| Không đủ điều kiện | denied | Quote bằng 0; không gọi host để hoàn |
| Quote dương nhưng host từ chối | denied | Giữ quote đầy đủ; host ghi policy_denied |
| Host chấp nhận | resolved | Kết quả lấy khoản đã ghi từ ledger |
| Claim không tồn tại hoặc xung đột số tiền | failed | Không sửa khoản đã commit |

Ví dụ quan trọng: đơn đã hoàn 30.000 đồng, nay được hưởng tổng 150.000 đồng.
Shape gửi quote 150.000; host chỉ ghi thêm 120.000 nếu approval cho phép.
`proposal_amount` vẫn là 150.000. Nếu shape tự trừ trước, host sẽ trừ hai lần.

Môi trường có sẵn Python 3.12.2 và virtualenv. Mọi lệnh sau chạy trong `src/`;
dùng trực tiếp `.\.venv\Scripts\python.exe` không cần activate PowerShell.

```powershell
.\.venv\Scripts\python.exe -m lab8.smoke
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts=
```

Kết quả trước triển khai: smoke pass; host 54 passed, 248 deselected;
student 186 failed, 62 passed, 54 deselected. Đây là số thực đo trên checkout này.
Đỏ ở student là do ba shape còn stub; không phải lý do sửa test hoặc thước đo.

## CP2: Cùng nghiệp vụ, thay cách điều phối

Workflow đọc claim → đọc đơn đúng chủ → tính quote bằng code → gửi host → finish.
Không cần gọi model nếu các bước đã xác định rõ. Tiền luôn qua host.

Single dùng `run_react` với tối đa 8 bước và `worker=True`: đọc đơn → tính quote
qua tool → kết thúc vòng lặp. Sau vòng lặp shape mới gửi quote sang host.
Mỗi lượt decide gọi MockLLM và tính usage thật của mô phỏng vào budget.
MockLLM ở repo chỉ trả chuỗi có seed, không trả tool call có cấu trúc: adapter
trong shape ánh xạ observation thành hành động đọc theo quy tắc. Đây là giới hạn
của harness, không phải bằng chứng model thật biết tự lập kế hoạch.

Orchestrator tạo handoff bằng allowlist, giao đọc đơn/chính sách/quote cho
investigator, nhận kết quả rồi gửi host. Investigator không được ghi tiền.

Kiểm từng shape:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k workflow
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k 'single and not workflow and not orchestrator and not swarm'
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k orchestrator
```

Lệnh `-k single` đơn lẻ còn chọn tên hàm `test_public_single_run_cases` của các
shape khác. Bộ lọc trên loại các shape kia để thấy đúng 62 test của single.

Tự giải thích trước khi chuyển bước: cả ba shape khác nhau ở cách điều phối;
vì sao số tiền, approval và ghi ledger vẫn phải theo cùng một host?

## CP3: An toàn khi chuyển việc và khi chạy lại

Handoff chỉ chứa trường được phép và công cụ chỉ đọc. Không chuyển parent
context; không ghi ticket, secret, header hoặc order row thô vào trace.
Tóm tắt bằng model vẫn có thể chép lại bí mật nên không thay được allowlist.

Khi gọi host, chuyển tiếp `crash_at` và để `InjectedCrash` lan ra caller.
Khối finally ghi trace an toàn và đóng kết nối, không chuyển crash thành một
RunResult thành công. Chạy lại cùng claim trên cùng database để mô phỏng resume.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k 't11 or t12'
.\.venv\Scripts\python.exe -m pytest -q tests/test_handoff_secret.py tests/test_trace_contract.py
.\.venv\Scripts\python.exe -m lab8.demo.buggy_workflow
```

Demo cố ý tạo hai dòng refund: ghi tiền đã thành công nhưng checkpoint chưa
lưu, resume chỉ nhìn checkpoint nên ghi thêm. Host thật dùng idempotency key
`refund:{claim_id}`, ràng buộc duy nhất và transaction ghi refund cùng audit.
Ledger mới là bằng chứng đã ghi effect; checkpoint riêng lẻ không đủ.

Hai kiểu chống hoàn trùng khác nhau: idempotency chặn cùng claim ghi lại;
trần theo đơn chặn nhiều claim khác nhau cùng đòi phần tiền đã hoàn.

## Thông tin nhóm và phần chuẩn bị bài nộp

- Đã xác nhận nhóm MHT và đầy đủ thông tin, vai trò: Vũ Mạnh Hoạch — workflow + integration; Nguyễn Văn Tùng — single; Nguyễn Đắc Tuấn Nghĩa — orchestrator + handoff; Võ Công Minh — ledger + evaluation.
- Đọc và chạy các ví dụ trên, ghi đóng góp thật và test thật vào bảng đóng góp.
- Không suy ra kết quả hidden hoặc model sản xuất từ test public.
- Benchmark, ADR lựa chọn kiến trúc và bài nộp đầy đủ thuộc CP4–CP5, chưa nằm trong đợt này.

## Bằng chứng kiểm tra sau triển khai

- Mỗi shape workflow, single, orchestrator: 62 test student passed.
- Hai file test handoff/trace: 9 passed.
- Kiểm tra cú pháp: `python -m compileall -q lab8/shapes` thành công.
- Toàn bộ suite, gồm host và student: `python -m pytest -q -o addopts=` → 302 passed.
- Không có cấu hình hoặc công cụ mypy/pyright trong môi trường; compileall không thay thế kiểm tra kiểu tĩnh.
- Không sửa host, policy, durability, metrics, config hoặc dữ liệu đề bài.
- Chưa thêm test mới khi seam bổ sung chưa được người dùng xác nhận; đợt này dùng các test sẵn có.

## Review sau triển khai

Mốc trước thay đổi: `034c6c421c198dae67a9211d15e2587d5a378972`.
Commit triển khai: `fb6f0e5`.

- Standards: không phát hiện vi phạm cần sửa. Phần setup/kết thúc tương tự giữa
  ba shape được giữ trong từng file để phù hợp phạm vi file grader nhận.
- Spec: không phát hiện lỗi cần sửa trong phần đã triển khai. Khi review, Ticket 02
  còn chờ thông tin nhóm; sau đó người dùng đã xác nhận đầy đủ, ticket đã hoàn thành.
- Chỉ sửa định dạng Markdown sau lượt chạy cuối 302 passed; không thay đổi code.
