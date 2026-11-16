# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Vũ Mạnh Hoạch | | | | Workflow + integration |
|   2 | Nguyễn Văn Tùng | 2A202603471 | nguyenvantung011204@gmail.com | Nguyenvantung04 | Single agent |
|   3 | Nguyễn Đắc Tuấn Nghĩa | | | dacnghia-lx | Orchestrator + handoff |
|   4 | Võ Công Minh | | | VOX304 | Ledger + evaluation |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Văn Tùng | Single agent | ddb1169 | src/tests/test_single_agent.py |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603471_NguyenVanTung

### Phần việc phụ trách

- Single agent (Shape B - ReAct loop) tại `src/lab8/shapes/single.py`.

### Đóng góp cụ thể

- Triển khai ReAct loop với max 8 steps, sandbox `worker=True` chỉ cho phép công cụ đọc.
- Cơ chế không tin dữ liệu ticket của khách, luôn tra cứu DB đơn hàng để tính bồi thường thực tế.
- Tách quyền ghi duy nhất cho Host và xử lý an toàn crash injection.
- Viết bộ kiểm thử `src/tests/test_single_agent.py`.

### Bằng chứng

- Commit `ddb1169`.
- Báo cáo chi tiết: `report/team/2A202603471_NguyenVanTung.md`.
- Test passed: `src/tests/test_single_agent.py` và 62/62 test case `single` trong `test_public_matrix.py`.
