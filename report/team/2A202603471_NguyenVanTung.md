# Báo cáo cá nhân — Nguyễn Văn Tùng

> **Lưu ý**: Đổi tên file thành `<MSSV>_NguyenVanTung.md` trước khi nộp chính thức theo quy định của môn học (ví dụ: `20211234_NguyenVanTung.md`).

---

## 1. Thông tin thành viên

- **Họ tên**: Nguyễn Văn Tùng
- **MSSV**: 2A202603471
- **Email**: nguyenvantung011204@gmail.com
- **GitHub**: Nguyenvantung04

---

## 2. Phần việc phụ trách

- **Vai trò trong nhóm**: Single Agent (Shape B).
- **Module phụ trách**:
  - Triển khai toàn bộ logic xử lý khiếu nại bằng mô hình tác tử đơn (ReAct loop) tại `src/lab8/shapes/single.py`.
  - Thiết kế và bổ sung bộ kiểm thử đơn vị độc lập cho Single Agent tại `src/tests/test_single_agent.py`.
  - Đảm bảo shape `single` vượt qua toàn bộ ma trận kiểm thử public benchmark (T01–T14), kịch bản gọi lại (T11 - Retry idempotency) và sự cố ngắt nguồn (T12 - Crash before checkpoint).

---

## 3. Đóng góp cụ thể

### 3.1. Các quyết định kỹ thuật và triển khai mã nguồn (`src/lab8/shapes/single.py`)

1. **Vòng lặp ReAct có kiểm soát (Max 8 steps & Least Privilege)**:
   - Sử dụng runtime `run_react(..., max_steps=8, worker=True)` kết hợp hàm `decide(seen)` để đưa ra chuỗi hành động tuần tự:
     $$\text{get\_claim\_view} \longrightarrow \text{lookup\_order} \longrightarrow \text{compute\_compensation} \longrightarrow \text{lookup\_refund\_history} \longrightarrow \text{final decision}$$
   - Bật cờ `worker=True` nhằm cưỡng chế sandbox runtime: agent chỉ được truy cập vào danh mục công cụ đọc an toàn (`READONLY_TOOLS`), tuyệt đối bị cấm gọi công cụ ghi tiền (`issue_refund`).

2. **Cơ chế phòng thủ - Không tin dữ liệu từ người dùng (Distrust ticket text)**:
   - Tại Bước 2 của hàm `decide()`, văn bản ticket của khách (ví dụ: claim C-002 khách khai báo *"giao trễ 9 ngày"*) chỉ được dùng để gửi qua `mock_llm.complete(..., purpose="parse")` nhằm hạch toán chi phí mô hình (Budget).
   - Agent không căn cứ vào lời khách khai mà bắt buộc phải gọi công cụ `lookup_order` để lấy bản ghi dữ liệu đơn hàng thực tế từ database, sau đó chuyển `order_result["order"]` vào `compute_compensation` để tính mức bồi thường thực tế.

3. **Tách biệt vai trò Host - Agent trong xử lý tài chính & Per-order cap**:
   - Agent chỉ đóng vai trò phân tích, tra cứu lịch sử qua `lookup_refund_history` và đề xuất mức bồi thường (`proposal_amount` - full quote) mà không tự ý cấn trừ tiền.
   - Host là thành phần duy nhất giữ quyền ghi tài chính (`single writer`), thực hiện thẩm định và kích hoạt giao dịch thông qua `durability.issue_refund(conn, claim_id, proposal_amount, crash_at=crash_at)`.

4. **Độ bền vững khi gặp sự cố (Crash safety & Trace Contract v1)**:
   - Truyền nguyên vẹn tham số `crash_at` vào `durability.issue_refund` và không dùng khối `try/except` để bắt `InjectedCrash`, bảo đảm hệ thống thử nghiệm crash đúng thời điểm `after_effect_before_checkpoint` (T12).
   - Thực hiện `trace.write()` ngay trước lệnh ghi tiền để đảm bảo trace log được lưu xuống đĩa kể cả khi có crash xảy ra.
   - Tuân thủ nghiêm ngặt Trace Contract: không ghi bất kỳ thông tin nhạy cảm (PII, secret canary, token) vào các observation hay event payloads.

### 3.2. Viết kiểm thử bổ sung (`src/tests/test_single_agent.py`)

Đã thiết kế và bổ sung bộ test độc lập kiểm tra các ràng buộc trọng yếu của Single Agent:
- `test_single_agent_distrusts_ticket_delay`: Kiểm tra case C-002 khách phóng đại thời gian trễ nhưng DB ghi nhận 2 ngày $\rightarrow$ Agent phải từ chối (`denied`, 0 VND).
- `test_single_agent_step_cap_within_limit`: Kiểm tra luồng claim thành công hoàn tất trong ngân sách bước $\le 8$.
- `test_single_agent_missing_order_needs_info`: Kiểm tra xử lý claim thiếu thông tin đơn hàng (C-004) chuyển trạng thái `needs_info`.

---

## 4. Bằng chứng

- **Commit chính**: `ddb1169` (`feat(single-agent): implement ReAct single agent, unit tests, and personal report`)
- **Files đã tạo / chỉnh sửa**:
  - `src/lab8/shapes/single.py`: Triển khai đầy đủ hàm `run_claim` cho Single Agent.
  - `src/tests/test_single_agent.py`: Bổ sung 3 test case chuyên biệt cho shape `single`.
- **Kết quả chạy kiểm thử thực tế**:
  - Chạy `python -m pytest src/tests/test_single_agent.py`: **3/3 PASSED (100%)**.
  - Chạy `python -m pytest -m student -o addopts= -k "single]"`: **62/62 test cases PASSED (100%)** trong ma trận `test_public_matrix.py` (toàn bộ T01–T14 trên các seed 11, 22, 33, 44, 55 và các test T11, T12).
  - Chạy bộ kiểm thử tự động `python -m lab8.check_submission`:
    ```text
    == shapes ==
    [ OK ] shape single: format đúng, 12/12 claim public pass ở seed 11
    ```
- **Mẫu Run ID & Trace sinh ra**:
  - Run ID: `R-single-C-001-s11`
  - Trace file: `traces/R-single-C-001-s11.json`
  - Trạng thái trả về: `status="resolved"`, `proposal_amount=35000`, `model_calls=5`, `tool_calls=4`.

---

## 5. Công cụ AI đã dùng

- **Công cụ**: Trợ lý AI Antigravity (Google DeepMind).
- **Mục đích sử dụng**:
  - Hỗ trợ rà soát luồng điều phối trạng thái tích lũy trong vòng lặp ReAct (`decide(seen)`).
  - Kiểm tra tính tuân thủ quy chuẩn Trace Contract v1 (loại bỏ PII/canary secret khỏi payload trace).
  - Soạn thảo các test case biên (`src/tests/test_single_agent.py`).
- **Cách tự kiểm tra và thẩm định lại**:
  - Không sao chép mù quáng: tự tay đọc kỹ logic mã nguồn `run_react` và `durability.issue_refund`.
  - Kiểm chứng bằng lệnh chạy thực tế trên máy: chạy trực tiếp test qua `pytest`, kiểm tra log SQLite và kiểm tra file trace JSON thực tế trên ổ cứng.
  - Chạy công cụ chấm chuẩn hóa của lab `python -m lab8.check_submission` để đảm bảo không bị cảnh báo lỗi format.

---

## 6. Tự đánh giá

- **Mức độ hoàn thành**: 100% nhiệm vụ được giao cho vai trò Single Agent.
- **Điểm mạnh của giải pháp**:
  - Kiến trúc rõ ràng: phân tách rành mạch giữa quan sát (Observation), suy luận (Decide) và thực thi (Host execution).
  - An toàn bảo mật: triệt để áp dụng nguyên tắc đặc quyền tối thiểu (Least Privilege) với `worker=True`, bảo vệ tài chính công ty trước các tác tử AI tự phát.
  - Khả năng chống chịu sự cố cao: đáp ứng hoàn hảo tiêu chí Idempotency và Crash durability.
- **Điểm cần lưu ý khi thảo luận nhóm**:
  - Shape Single tiêu tốn nhiều model call hơn dạng Workflow tuyến tính cố định (5 model calls vs ít hơn ở Workflow), nhưng có tính linh hoạt cao hơn trong việc xử lý các trường hợp ngoại lệ hoặc phân nhánh động.
