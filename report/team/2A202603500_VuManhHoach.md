# Báo cáo cá nhân — 2A202603500_VuManhHoach

## 1. Thông tin thành viên

- Họ tên: Vũ Mạnh Hoạch
- MSSV: 2A202603500
- Email: 26ai.hoachvm@vinuni.edu.vn
- GitHub: https://github.com/vumanhhoach2003

## 2. Phần việc phụ trách

**Workflow (Shape A) và Integration** trong Lab 8 — From Workflows to Agents (LogiX-VN).

- Hoàn thiện và kiểm thử `src/lab8/shapes/workflow.py` theo giao diện `run_claim(claim_id, *, seed, store_path, crash_at=None)`.
- Kiểm tra luồng xử lý claim hoàn phí vận chuyển qua các thành phần đọc dữ liệu claim/order, tính compensation, gọi host để ghi refund, ghi audit và xuất trace.
- Thực hiện kiểm thử riêng Workflow, kiểm thử tích hợp host, retry/idempotency, crash safety và benchmark toàn hệ thống sau khi các shape được ghép vào repo nhóm.
- Tổng hợp kết quả kiểm thử để hỗ trợ đánh giá và lựa chọn kiến trúc.

## 3. Đóng góp cụ thể

- **Workflow:** triển khai luồng xử lý xác định (deterministic), dùng dữ liệu order đáng tin cậy để tính quote, không dùng nội dung ticket làm nguồn quyết định số tiền hoàn. Việc ghi tiền được thực hiện qua `durability.issue_refund`, không ghi trực tiếp vào ledger.
- **Tích hợp và kiểm thử:** chạy bộ kiểm thử riêng Shape A, host tests, toàn bộ student tests, kiểm tra chạy lại claim trên cùng SQLite database và chạy crash suite.
- **Đối chiếu hành vi retry:** chạy hai lần `C-001` trên cùng `data/workflow_integration.sqlite`; cả hai lần trả về `resolved`, proposal 35.000 VND, một refund `committed` và `committed_audit_count = 1`.
- **Benchmark:** chạy 4 shape (`workflow`, `single`, `orchestrator`, `swarm`) trên 14 public claims với 5 seed (11, 22, 33, 44, 55), xuất `reports/benchmark.json`.
- **Quyết định kỹ thuật đề xuất:** ưu tiên Workflow trên bộ public vì đạt độ chính xác và độ ổn định tương đương Single/Orchestrator nhưng chi phí mô phỏng thấp nhất, đồng thời có mức tự chủ thấp nhất.
- **Commit chính:** `[CẦN ĐIỀN: hash commit thực tế chứa phần Workflow/Integration do bạn đóng góp]`. Lấy bằng `git log --oneline -- src/lab8/shapes/workflow.py` trong repo nhóm; không dùng hash chưa xác minh là của mình.
- **Test tự thêm/sửa:** `[CẦN XÁC NHẬN: tên file/test nếu bạn có viết thêm; nếu không, ghi "Không thêm test mới; sử dụng bộ test public có sẵn"]`.

## 4. Bằng chứng

| Hạng mục | Lệnh hoặc bằng chứng | Kết quả đã quan sát |
| --- | --- | --- |
| Workflow public tests | `python -m pytest -q -m student -o addopts= -k workflow` | **62 passed**, 240 deselected |
| Host tests | `python -m pytest -q` | **54 passed**, 248 deselected |
| Student tests toàn hệ thống | `python -m pytest -q -m student -o addopts=` | **248 passed**, 54 deselected |
| Chạy claim C-001 | `python -m lab8.run --shape workflow --claim-id C-001 --seed 11 --db data/workflow_integration.sqlite` | `resolved`, proposal **35.000 VND**, một refund `committed`, audit count **1** |
| Retry C-001 | Chạy lại cùng lệnh, cùng database | Refund vẫn chỉ có một bản ghi, audit count **1** |
| Crash safety | `python -m lab8.crash_test --count 20 --out reports/crash.json` | **20/20** |
| Benchmark | `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` | Đã tạo `reports/benchmark.json` |

- **Run ID dẫn chứng:** `R-workflow-C-001-s11`.
- **Trace:** `traces/R-workflow-C-001-s11.json` (file sinh khi chạy, không commit theo `.gitignore`).
- **Báo cáo crash:** `reports/crash.json` (20/20).
- **Benchmark public:** Workflow `pass = 1.000`, `pass^5 = 1.000`, `variance = 0.000000`, `cost/success = 34.29` VND mô phỏng; Single `1.000 / 1.000 / 0.000000 / 36.45`; Orchestrator `1.000 / 1.000 / 0.000000 / 47.85`; Swarm `0.986 / 0.929 / 0.000816 / 49.57`.
- **Kiểm tra định dạng nộp bài:** `python -m lab8.check_submission` xác nhận 3 shape, benchmark và crash report đạt; lần kiểm tra được cung cấp vẫn còn lỗi tài liệu nhóm (`decision_adr.md`, `research_card.md`, `TEAM.md`), nên chưa thể coi bài nhóm đã sẵn sàng nộp.
- **Link commit:** `[CẦN ĐIỀN: URL commit thực tế trên GitHub repo nhóm]`.

## 5. Công cụ AI đã dùng

- **Công cụ:** ChatGPT (OpenAI).
- **Mục đích sử dụng:** hỗ trợ tìm hiểu yêu cầu Lab 8, phân biệt nhiệm vụ Workflow và Integration, tham khảo cách triển khai Workflow, hướng dẫn các lệnh kiểm thử, giải thích kết quả terminal và hỗ trợ soạn báo cáo cá nhân.
- **Cách tự kiểm tra:** trực tiếp chạy lệnh trong môi trường Python `.venv` của repo nhóm; đối chiếu kết quả pytest, chạy lại claim trên cùng database, chạy crash suite 20 điểm, benchmark 4 shape và `check_submission`. Các kết luận về kết quả chỉ dựa trên log thực tế đã quan sát; không coi nội dung do AI đề xuất là bằng chứng thay cho test.

## 6. Tự đánh giá

Tôi đã hoàn thành phần triển khai và kiểm thử public của Workflow, đồng thời thực hiện các bước Integration chính trên mã nguồn đã ghép của nhóm. Workflow vượt qua 62/62 bài test public; bộ host đạt 54/54, student tests toàn hệ thống đạt 248/248 và crash safety đạt 20/20. Benchmark public cho thấy Workflow đạt pass rate và pass^5 bằng 1.000, variance bằng 0, với chi phí mô phỏng thấp nhất trong bốn kiến trúc.

Qua phần việc này, tôi hiểu rõ hơn sự khác biệt giữa workflow xác định và các kiến trúc agent, vai trò của host trong việc kiểm soát thao tác ghi tiền, tính idempotency khi retry và yêu cầu crash recovery. Tôi cũng rút ra rằng lựa chọn kiến trúc nên dựa trên độ chính xác, độ ổn định, chi phí và mức tự chủ cần thiết thay vì mặc định dùng nhiều agent.

**Giới hạn:** các số liệu trên đến từ bộ public; chưa có kết quả chấm hidden của giảng viên. Phần báo cáo và thông tin commit của nhóm cần được hoàn thiện, xác nhận trước khi nộp chính thức.
