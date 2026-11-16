# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 — đo overhead của một bước đọc trong kế hoạch investigator. Không thay đổi số agent. |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Kim et al., Towards a Science of Scaling Agent Systems, arXiv v3 (08/04/2026), https://arxiv.org/abs/2512.08296v3. Bằng chứng: thí nghiệm kiểm soát trong nghiên cứu, không phải báo cáo production. |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Trong các cấu hình nghiên cứu, tác vụ dùng nhiều tool có thể chịu overhead của multi-agent; đánh giá kiến trúc cần kiểm soát tools, prompts và compute. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Nguồn v3: 260 cấu hình, 6 benchmark, 5 kiến trúc, 3 họ LLM. Lab chỉ dùng MockLLM và 14 claim giả lập; không tái lập kết quả paper hay đo scaling theo số agent. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Ghi trước khi chạy ablation: bỏ lookup_refund_history khỏi kế hoạch investigator sẽ giữ nguyên pass rate/pass^5 và quyết định tiền; tiết kiệm 1 tool call mỗi trial có handoff, tổng 65 call trên 70 trial. Cost/success giảm, model calls/token giữ nguyên. Host vẫn tự kiểm lịch sử. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ nguyên model/prompt/seed, 14 claim, world, registry tool và quyền host, bảng giá, evaluator và database mới mỗi trial. Chỉ đổi kế hoạch có/không gọi tool đọc lịch sử trong investigator. Nạp bản orchestrator vào module riêng; đổi nhãn shape/run id để tách trace, không sửa shape chính thức. |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Nếu shape phụ thuộc đọc lịch sử để tự trừ quote thì C-013/C-014 có thể sai; đo pass rate, pass^5, cost/success, model/tool calls và kiểm các ca crash. So từng claim/seed, không chỉ nhìn điểm tổng. |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn):
- Run id / file report:
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu:
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
