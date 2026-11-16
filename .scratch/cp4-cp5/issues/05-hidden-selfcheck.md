# 05: CP5: Tự kiểm dữ liệu hidden được phát

**What to build:** Nếu nhận dữ liệu thì chạy self-check có trace/error/leak flags, không suy ra pass rate khi thiếu nhãn.

**Blocked by:** 01; điều kiện bên ngoài: có bộ dữ liệu student_drop do giảng viên phát.

**Status:** waiting-for-data

- [x] Đã kiểm tra: không có bộ student_drop hoặc cặp hidden claims/world trong workspace. Đã ghi trạng thái và lệnh chạy khi có dữ liệu.
- [ ] Chỉ chạy khi có đủ claims/world; không tạo dữ liệu giả thay cho bộ hidden.
