# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 06279a5
- Run id dẫn chứng: R-workflow-C-001-s11, R-workflow-C-002-s55, R-workflow-C-014-s55 (src/reports/benchmark.json); so sánh R-swarm-C-002-s55
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0 (70/70 trial, 14 claim × seed 11,22,33,44,55, src/reports/benchmark.json)
- Cost per success (mô phỏng, VND): 34.29 (workflow) so với single 36.45, orchestrator 47.85, swarm 49.57
- Crash safety: 20/20 (src/reports/crash.json); thêm 9 ca crash end-to-end cho workflow/single/orchestrator trong src/tests/test_evaluation_safety.py
- Secret leak / approval bypass: 0 / 0 trên bộ public và các ca trong test_evaluation_safety.py (15 ca approval hỏng, 3 ca quét stdout/artifact); chưa có số hidden

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng corpus public (14 claim), cùng 5 seed, cùng MockLLM, bảng giá, evaluator và database mới cho mỗi trial (`src/reports/benchmark.json`, 280 trial), cả ba shape nhóm viết đều đạt 70/70, pass^5 = 1 và variance = 0. Độ đúng không phân biệt được ba shape, nên nhóm chọn theo tiêu chí tiếp theo: ít tự chủ nhất và rẻ nhất. Workflow có cost/success thấp nhất (34.29 VND mô phỏng), không gọi model lần nào (0 model call trung bình, so với single 4.43 và orchestrator 2.00), mean/p95 steps 3.79/5. Mọi quyết định (thiếu đơn, sai chủ đơn, quote, gọi host) là nhánh Python cố định đọc từ order row, nên chữ trong ticket không có đường nào đi vào số tiền. Swarm là bản duy nhất sai (`R-swarm-C-002-s55`: tin ticket "trễ 5 ngày" thay vì order row 2 ngày, trả `resolved` thay vì `denied`), đúng loại lỗi mà workflow loại bỏ bằng cấu trúc.

## Có đáng đổi lấy multi-agent không

Không, với dữ liệu hiện có. Orchestrator đạt cùng pass rate nhưng cost/success cao hơn 40% (47.85 so với 34.29) và cần 2 model call mỗi claim; swarm đắt nhất và là bản duy nhất có variance. Ngay cả khi một shape multi-agent nhỉnh hơn vài phần trăm pass rate, nhóm chỉ đổi nếu chênh lệch lớn hơn độ dao động giữa các seed và không kéo theo variance cao hơn. Quyết định sẽ đảo lại nếu: (1) bộ hidden có loại claim mà luồng cố định không xử lý được (ví dụ cần đọc chứng từ phi cấu trúc, phải chọn tool theo tình huống), khiến workflow rơi dưới 0.75 trong khi single/orchestrator vẫn đạt; (2) bài toán cần nhiều bước tra cứu độc lập chạy song song, khi đó tách investigator mới có lợi; (3) yêu cầu tách quyền (người đọc dữ liệu khác người ghi tiền) trở thành ràng buộc kiểm toán bắt buộc. Lưu ý: so sánh này là giữa các bản triển khai hoàn chỉnh, không cô lập nhân quả của topology, vì số model call, prompt và cách ghi trace của các shape khác nhau.

## Trace và bằng chứng

Trace workflow ghi các event: `quote` (amount_vnd, reason), `refund_history` (refund_count, refunded_vnd), `host_call` (amount_vnd), `host_result`, và `final` (status, proposal_amount, reason). Trace được ghi xuống đĩa trước khi gọi host để vẫn hợp lệ nếu crash. Cố ý **không** ghi: claim row (có `parent_secret`, `raw_headers`), nội dung ticket, `principal_id`, và order row thô (có SĐT, địa chỉ, tên hàng, `internal_note`); chỉ ghi các field đã qua `get_claim_view`, `lookup_order` và kết quả quote. Orchestrator chỉ ghi handoff đã qua allowlist (`make_handoff` + `sanitize`). Bằng chứng: `src/tests/test_orchestrator_shape.py` quét trace của cả 14 claim tìm canary và giá trị PII từ fixture; `src/tests/test_evaluation_safety.py` quét stdout/stderr và artifact của ca C-010. Nếu có log nằm ngoài chỗ scanner quét, nhóm không coi đó là bằng chứng sạch: contract yêu cầu mọi file shape ghi phải nằm cạnh trace với tên `<run_id>*`, và shape của nhóm không ghi file nào khác, không in dữ liệu claim ra stdout.

## Giới hạn

MockLLM không phải model sản xuất; với model thật, single và orchestrator có thể dao động nhiều hơn còn workflow không bị ảnh hưởng vì không gọi model. Latency để `unavailable`. Giá là mô phỏng, không phải hóa đơn API. Chưa có dữ liệu `student_drop/` nên chưa tự kiểm hidden; pass rate hidden do giảng viên chấm. Không sửa JSON trong `src/reports/` bằng tay.
