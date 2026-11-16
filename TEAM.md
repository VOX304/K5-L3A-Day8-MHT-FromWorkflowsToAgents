# Team

## Thông tin nhóm

- Tên nhóm: MHT
- Lớp: L3A
- Repo nhóm: `K5-L3A-Day8-MHT-FromWorkflowsToAgents`
- URL repo: https://github.com/VOX304/K5-L3A-Day8-MHT-FromWorkflowsToAgents
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
| 1 | Nguyễn Đắc Tuấn Nghĩa | 2A202603442 | orange25k5@gmail.com | https://github.com/dacnghia-lx | Orchestrator + handoff |
| 2 | Vũ Mạnh Hoạch | 2A202603500 | 26ai.hoachvm@vinuni.edu.vn | https://github.com/vumanhhoach2003 | Workflow + integration |
| 3 | Nguyễn Văn Tùng | 2A202603471 | nguyenvantung011204@gmail.com | https://github.com/Nguyenvantung04 | Single |
| 4 | Võ Công Minh | 2A202503520 | congminhvox@gmail.com | https://github.com/vox304 | Ledger + evaluation |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Đắc Tuấn Nghĩa | Orchestrator + handoff | d33bd49 | src/tests/test_orchestrator_shape.py (20 ca) |
| Vũ Mạnh Hoạch | Workflow + integration | 07dba1e | |
| Nguyễn Văn Tùng | Single agent | ddb1169 | src/tests/test_single_agent.py |
| Võ Công Minh | Ledger + evaluation (có trợ lý AI hỗ trợ thực thi; không nhận tác giả code shape của thành viên khác) | e27e680 | src/tests/test_evaluation_safety.py (33 ca), src/tests/test_evaluation_ablation.py (9 ca) |

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
