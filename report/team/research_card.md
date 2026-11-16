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

- Lệnh đã chạy (trong `src/`, PowerShell):

```powershell
.\.venv\Scripts\python.exe -m lab8.benchmark --shapes orchestrator,orchestrator_no_history --extra-shape orchestrator_no_history=bonus.orchestrator_no_history:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_history.json
```

- Phiên bản code đo: `e27e680`.
- Run id / file report: `src/reports/ablation_history.json`; ví dụ `R-orchestrator-C-014-s55` và `R-orchestrator_no_history-C-014-s55`.
- Kết quả: hypothesis đúng trong corpus này. Cả hai bản đạt 70/70 trial, pass rate = pass^5 = 1, variance = 0. Không có khác biệt theo cặp claim/seed về passed/status/reason/model_calls. Baseline trong ablation khớp toàn bộ 70 row baseline trong benchmark chính thức.
- Tool calls giảm tổng 65; model calls giữ 140 ở mỗi bản. Tổng cost mô phỏng giảm từ 3.349,70 xuống 2.699,70 VND (650 VND, khoảng 19,40%). Cost/success giảm từ 47,852857 xuống 38,567143 VND. Mean/p95 trace steps giữ 5,357143/6.
- Giải thích: host vẫn đọc lại lịch sử trong transaction; bước đọc trước đó của investigator ở phiên bản này chỉ thêm thông tin vào trace, không quyết định số tiền. Khi bỏ bước này, trường refunded_vnd trong trace có thể là null; tính quan sát lịch sử bị giảm dù quyết định tiền không đổi.
- Không kết luận rằng mọi tool lịch sử đều dư thừa hoặc ít agent luôn tốt hơn. Thí nghiệm không đổi số agent; không sửa bản orchestrator chính thức. Metric steps đếm event trace, không phải số tool call nên không giảm trong ablation này.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
