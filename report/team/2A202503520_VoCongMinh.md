# Báo cáo cá nhân — 2A202503520_VoCongMinh

## 1. Thông tin thành viên

- Họ tên: Võ Công Minh
- MSSV: 2A202503520
- Email: congminhvox@gmail.com
- GitHub: https://github.com/vox304
- Nhóm: MHT — lớp L3A

## 2. Phần việc phụ trách

Ledger + evaluation ở CP4 và CP5: kiểm chứng an toàn ghi hoàn tiền, tạo bằng chứng crash/benchmark, thực hiện ablation một biến và đối chiếu yêu cầu tài liệu. Phạm vi đợt này đến Ticket 05; quyết định kiến trúc chính thức và báo cáo nhóm chưa hoàn tất.

Phần host ledger, policy và durability là code có sẵn của lab. Tôi không nhận là người viết các thành phần đó, cũng không nhận tác giả workflow/single/orchestrator của các thành viên khác. Công việc kiểm thử, thực thi và soạn báo cáo dưới đây có trợ lý AI hỗ trợ, như nêu ở mục 5.

## 3. Đóng góp cụ thể

Commit kỹ thuật: [e27e680](https://github.com/VOX304/K5-L3A-Day8-MHT-FromWorkflowsToAgents/commit/e27e680). Đây là commit local của workspace, cần push để đường dẫn GitHub truy cập được.

- Bổ sung `src/tests/test_evaluation_safety.py`: 33 ca kiểm qua run_claim/RunResult và contract ledger/audit. Các ca phủ approval không hợp lệ, ba cửa sổ crash, hai claim cùng một đơn, xung đột hạn mức khi retry, và không lộ thông tin qua stdout/artifact.
- Bổ sung `src/tests/test_evaluation_ablation.py`: 9 ca kiểm biến thể không đọc history trước khi gửi host vẫn giữ quyết định tiền, model/token usage và an toàn crash.
- Thêm `src/bonus/orchestrator_no_history.py`, tái sử dụng bản orchestrator của Nguyễn Đắc Tuấn Nghĩa bằng module độc lập. Chỉ bỏ bước đọc history ở investigator; host vẫn kiểm lịch sử trong transaction. Đây là thí nghiệm research card, không phải đăng ký bonus.
- Tạo bằng chứng máy sinh: crash 20/20, benchmark 280 trial, ablation 140 trial, JUnit của suite 364 test. Không sửa tay JSON hoặc thay đổi thước đo.
- Hoàn thiện research card R1 và bản giải thích kết quả tại `docs/cp4-cp5-evaluation.md`.

Tên test tiêu biểu:

- `test_shape_rejects_invalid_approval_with_host_audit`
- `test_shape_crash_resume_and_second_retry_pay_once`
- `test_different_claims_cannot_pay_same_order_twice`
- `test_retry_with_changed_approval_keeps_original_effect`
- `test_shape_stdout_and_artifacts_do_not_expose_private_data`
- `test_omitting_history_read_preserves_financial_result`
- `test_experimental_plan_keeps_host_crash_safety`

## 4. Bằng chứng và kết quả

Phiên bản code dùng đo: `e27e680`. Toàn bộ test sau bổ sung: **364 passed**, so với baseline 322 passed trước đợt evaluation.

| Bằng chứng | Kết quả |
| --- | --- |
| `src/reports/evaluation_tests.xml` | 364 test, không fail/error |
| `src/reports/crash.json` | crash_safety 20/20 |
| `src/reports/benchmark.json` | 4 shape × 14 claim × 5 seed = 280 trial |
| `src/reports/ablation_history.json` | 2 kế hoạch × 14 claim × 5 seed = 140 trial |

| Shape | Pass rate | Pass^5 | Cost/success (VND mô phỏng) |
| --- | ---: | ---: | ---: |
| workflow | 1 | 1 | 34,285714 |
| single | 1 | 1 | 36,450000 |
| orchestrator | 1 | 1 | 47,852857 |
| swarm | 0,985714 | 0,928571 | 49,566957 |

Ví dụ run ID: `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-014-s55`. Swarm sai một trial `R-swarm-C-002-s55`: tin số ngày trễ trong ticket thay vì order row, đúng điểm yếu cố ý của bản tham chiếu.

Ablation baseline và biến thể đều đạt 70/70; model calls giữ 140 mỗi bản. Bỏ bước đọc history ở investigator tiết kiệm 65 tool calls, giảm tổng cost từ 3.349,70 xuống 2.699,70 VND mô phỏng. Host vẫn giữ việc tính phần chênh lệch và chống hoàn trùng. Kết quả chỉ hỗ trợ kết luận cho thiết kế/corpus này; trace của biến thể mất thông tin history đã đọc trước.

Giải thích kỹ thuật dùng khi trình bày:

- Idempotency chặn cùng claim ghi tiền lần nữa. Trần theo order chặn nhiều claim khác nhau đòi lại tiền đã hoàn.
- Quote là quyền lợi đầy đủ; host mới trừ phần đã hoàn. Quote 150.000 không đồng nghĩa ledger sẽ ghi thêm 150.000.
- Checkpoint không thay thế ledger: crash sau effect nhưng trước checkpoint có thể khiến resume ghi lần hai nếu chỉ nhìn tiến độ.
- 20/20 của host cần đi kèm test crash qua từng shape; không tự chứng minh cả ba shape đều chuyển tiếp crash_at đúng.
- Steps đếm event trace, không phải số vòng ReAct hoặc thời gian thực; chi phí là mô phỏng, latency unavailable.

Ticket 05 còn chờ bộ `student_drop` từ giảng viên. Chưa có kết quả hidden và không khẳng định đạt ngưỡng hidden 0,75.
Lệnh tái lập đầy đủ ở [báo cáo evaluation](../../docs/cp4-cp5-evaluation.md).

## 5. Công cụ AI đã dùng

Sử dụng ChatGPT/Codex để đọc yêu cầu, đề xuất và tạo test, thực thi lệnh trong workspace, phân tích báo cáo JSON, xác minh nguồn nghiên cứu và soạn bản báo cáo này. Các số liệu trên lấy từ lần chạy công cụ thật, không phải số AI ước đoán.

Các lệnh thực thi trong đợt này do trợ lý chạy. Tôi đã cung cấp phân công và yêu cầu công việc; không coi kết quả tự động này là bằng chứng rằng tôi đã tự chạy tay, tự hiểu toàn bộ code hoặc tự viết toàn bộ test. Trước khi nộp, cần tự chạy lại các lệnh, đọc trace của ca refund/retry/crash và giải thích được các điểm kỹ thuật nêu trên.

Nguồn nghiên cứu: Kim et al., [Towards a Science of Scaling Agent Systems, arXiv v3](https://arxiv.org/abs/2512.08296v3), 08/04/2026. Lab dùng ý tưởng đánh giá kiểm soát và overhead; không tái lập số liệu của paper.

## 6. Tự đánh giá dựa trên bằng chứng

Sản phẩm trong phạm vi ledger + evaluation đã có test end-to-end, báo cáo máy sinh và thí nghiệm một biến có thể chạy lại. Điểm giới hạn là dữ liệu public nhỏ, MockLLM có seed và các shape có cách ghi trace khác nhau; không suy rộng thành kết luận về model sản xuất hoặc hiệu quả riêng của topology.

Phần còn lại: nhận dữ liệu hidden để tự kiểm, cùng nhóm chốt ADR, hoàn thiện báo cáo nhóm và kiểm gói nộp. Mức độ tự nắm kiến thức và điểm tự đánh giá cần do cá nhân xác nhận sau khi thực hành; báo cáo này không tự đặt điểm hoặc bịa trải nghiệm học tập.
