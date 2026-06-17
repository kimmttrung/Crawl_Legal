*   **Xây dựng Law Manifest (`law_manifest.json`):** Bộ từ điển cứng lưu trữ ánh xạ chính xác từ tên luật thông thường sang chuỗi định dạng chuẩn của BTC để phục vụ bước Hậu xử lý.
    *   **Synthetic Dataset:** Sử dụng mô hình lớn ngoài pipeline sinh tự động 500 - 1000 cặp `Question - Answer - Relevant Articles` để làm tập Train/Dev kiểm thử nội bộ.

---

### GIAI ĐOẠN 2: XÂY DỰNG BỘ BENCHMARK ĐÁNH GIÁ NỘI BỘ (12/06 – 14/06)
*Mục tiêu: Tạo thước đo kỹ thuật độc lập để liên tục cải tiến hệ thống mà không cần phụ thuộc vào cổng nộp bài của BTC.*

*   **Công việc cụ thể:**
    *   **Xây bộ Ground Truth Gold Standard:** Lọc ra 300 câu hỏi đại diện từ tập test, dán nhãn thủ công hoặc bán tự động (kiểm định kỹ) có đầy đủ `answer` tham chiếu và `relevant_articles` chuẩn chỉnh.
    *   **Đo lường Retrieval:** Viết script tính toán tự động các chỉ số $Recall@5$, $Recall@10$, $MRR$ và $Hit\ Rate$ của tầng tìm kiếm.
    *   **Đo lường Citation:** Đánh giá độ lệch giữa mảng `relevant_articles` hệ thống tìm được và nhãn chuẩn.
    *   **Đo lường QA (LLM Evaluator):** Cấu hình một mô hình local đóng vai trò Judge, nạp bộ tiêu chí của BTC để chấm điểm thử nghiệm chất lượng câu trả lời.
*   **Sản phẩm bàn giao (Deliverable):** File `evaluation_report.md` cập nhật liên tục sau mỗi lần thay đổi thuật toán.

---

### GIAI ĐOẠN 3: TRIỂN KHAI TRUY HỒI LAI (HYBRID RETRIEVAL) (14/06 – 18/06)
*Mục tiêu: Tối ưu hóa tầng tìm kiếm để đạt Recall tối đa, không bỏ sót thông tin cốt lõi.*

*   **Công việc cụ thể:**
    *   **Sparse Retrieval (BM25):** Tối ưu hóa BM25 cho tiếng Việt (loại bỏ stopwords pháp lý không mang nghĩa, tích hợp từ điển đồng nghĩa chuyên ngành SME như *Mặt bằng sản xuất $\rightarrow$ Địa điểm kinh doanh*).
    *   **Dense Retrieval:** Số hóa các chunk pháp lý bằng các mô hình nhúng mạnh mẽ, ưu tiên: `BGE-M3` hoặc `vietnamese-bi-encoder`. Lưu trữ vào Vector Database local (`Qdrant` hoặc `Milvus`).
    *   **Multi-Query Generation & Query Expansion:** Khi người dùng đặt câu hỏi, hệ thống tự động sử dụng LLM sinh ra 3 - 5 biến thể truy vấn khác nhau để bao quát toàn bộ từ khóa và ngữ nghĩa.
    *   **Metadata Filtering:** Nếu trong câu hỏi có chứa các dấu hiệu số hiệu văn bản (Ví dụ: "Nghị định 80"), hệ thống sẽ tự động áp bộ lọc cứng (Hard filter) để thu hẹp không gian tìm kiếm trong tập văn bản đó trước khi tính toán độ tương đồng.
    *   **RRF Fusion:** Kết hợp danh sách xếp hạng từ BM25 và Vector Search bằng thuật toán **Reciprocal Rank Fusion (RRF)** thu về Top 30 ứng viên xuất sắc nhất.

---

### GIAI ĐOẠN 4: TÁI XẾP HẠNG VÀ TỐI ƯU HÓA TRUY HỒI (18/06 – 21/06)
*Mục tiêu: Sử dụng các mô hình tương quan chuỗi sâu để nhặt ra đúng Top 3 - Top 5 văn bản cốt lõi nhất.*

*   **Công việc cụ thể:**
    *   **Cross-Encoder Deployment:** Đưa Top 30 ứng viên từ Giai đoạn 3 chạy qua mô hình tái xếp hạng local như `bge-reranker-large`, `bge-reranker-v2` hoặc `Qwen-Reranker`.
    *   **Hard Negative Mining:** Thiết lập quy trình huấn luyện/lọc các đoạn văn bản có từ khóa giống nhau nhưng nội dung không liên quan để huấn luyện tư duy phân biệt cho tầng Reranker.
    *   **Chọn lọc Context:** Lọc lấy Top 3 - Top 5 Điều luật có điểm số Cross-Encoder vượt ngưỡng (Threshold) quy định để làm Context nạp vào LLM.

---

### GIAI ĐOẠN 5: XÂY DỰNG LLM & GENERATION PIPELINE (21/06 – 25/06)
*Mục tiêu: Sinh câu trả lời chuẩn logic pháp lý, gãy gọn và ép từ khóa thành công.*

*   **Công việc cụ thể:**
    *   **Triển khai Local LLM Engine:** Cài đặt mô hình chạy qua hạ tầng `vLLM` hoặc `Ollama` để tối ưu tốc độ sinh chuỗi. 
        *   *Mô hình ưu tiên:* **`DeepSeek-R1-Distill-Qwen-14B`** (Tận dụng khả năng suy luận chuỗi tư duy `<think>` sâu sắc) hoặc **`Qwen2.5-14B-Instruct`**.
    *   **Prompt Design Chặt chẽ:** Thiết kế System Prompt ép cấu hình đầu ra của LLM. Bắt buộc câu trả lời trong trường `answer` phải viết tường minh cấu trúc: *"Căn cứ vào Điều X của Văn bản A..."* hoặc *"Theo quy định tại Điều X..."*.
    *   **Answer Structure:** Thiết lập định dạng câu trả lời thân thiện với SME gồm 4 phần rõ rệt:
        1. Kết luận ngắn gọn/Phương án giải quyết sơ bộ.
        2. Căn cứ pháp lý trực tiếp (Chứa từ khóa "Điều X").
        3. Phân tích chi tiết điều kiện, nghĩa vụ hoặc mức xử phạt.
        4. **Cảnh báo giới hạn trách nhiệm của AI** theo đúng quy chế mục tiêu số 4 của BTC.

---

### GIAI ĐOẠN 6: LỚP TỰ KIỂM TRA CHỐNG ẢO GIÁC (SELF-VERIFICATION) (25/06 – 27/06)
*Mục tiêu: Chốt chặn an toàn (Anti-Hallucination) loại bỏ hoàn toàn các lỗi bịa luật hoặc suy diễn vô căn cứ.*

*   **Công việc cụ thể:**
    *   Xây dựng một Module kiểm định tự động chạy song song sau khi LLM sinh câu trả lời, quét qua 5 luật nghiêm ngặt:
        *   *Rule 1 (Context Check):* Điều luật LLM trích dẫn trong câu trả lời có nằm trong Context đầu vào không?
        *   *Rule 2 (Existence Check):* Số hiệu Điều luật đó có thực sự tồn tại trong kho dữ liệu gốc không?
        *   *Rule 3 (Manifest Alignment):* Tên văn bản đi kèm có khớp hoàn toàn với quy chuẩn trong `law_manifest.json` không?
        *   *Rule 4 (No Over-inference):* Câu trả lời có chứa thông tin khẳng định nào nằm ngoài phạm vi Context cung cấp không?
        *   *Rule 5 (At-least-one Check):* Có chứa ít nhất một cụm từ "Điều X" nào xuất hiện không?
    *   **Cơ chế xử lý:** Nếu vi phạm bất kỳ quy tắc nào, hệ thống lập tức kích hoạt lệnh **Regenerate (Sinh lại)** với tham số Temperature điều chỉnh thấp xuống.

---

### GIAI ĐOẠN 7: HẬU XỬ LÝ & ĐÓNG GÓI BÀI NỘP CHUẨN FORMAT (27/06 – 29/06)
*Mục tiêu: Trích xuất thông tin, điền chính xác vào cấu trúc JSON của BTC và xuất file nộp bài không tì vết.*

*   **Công việc cụ thể:**
    *   **Regex Extraction:** Tuyệt đối không bắt LLM tự sinh ra mảng JSON `relevant_docs` hay `relevant_articles` (LLM nhỏ dưới 14B rất dễ làm vỡ cấu trúc cú pháp JSON khi chạy hàng loạt). Hãy để LLM sinh dạng Text, sau đó dùng hàm Python Regex bóc tách các cụm từ "Điều X" ra ngoài.
    *   **Hard-Mapping:** Đối chiếu các Điều và Văn bản vừa bóc tách được với file từ điển cấu hình cứng `law_manifest.json` được thiết lập từ Giai đoạn 1. Tự động chuyển đổi và ghi đè vào file JSON theo đúng công thức: `Loại văn bản + Mã văn bản + Trích yếu` (Ví dụ: `04/2017/QH14|Luật Hỗ trợ doanh nghiệp nhỏ và vừa|Điều 4`).
    *   **Data Validation Script:** Chạy script kiểm tra toàn diện cấu trúc file `results.json`: Đảm bảo đủ 2000 bản ghi, không bản ghi nào bị null hay trống trường thông tin, các ID khớp hoàn toàn với file gốc của BTC.
    *   **Đóng gói (Submission Packaging):** Thực hiện nén zip trực tiếp file `results.json` nằm ngay ở thư mục gốc (không bọc thư mục con) theo đúng cú pháp hệ điều hành BTC yêu cầu. Hoàn thành và nộp bài trước hạn chót 24h - 48h để phòng ngừa rủi ro nghẽn mạng.

---

## IV. SƠ ĐỒ PHÂN CHIA NHÂN SỰ VÀ TRÁCH NHIỆM TRONG ĐỘI

Để tiến độ vận hành nhịp nhàng, công việc được chia nhỏ dựa trên vai trò chuyên môn của từng thành viên trong nhóm:

| Thành viên | Vai trò | Nhiệm vụ chính phụ trách | Sản phẩm cốt lõi cần bàn giao |
| :--- | :--- | :--- | :--- |
| **Thành viên A** | **Data Engineer** | Giai đoạn 0 & Giai đoạn 1: Khảo sát thực thể, phân cụm câu hỏi, viết script cào dữ liệu, thực hiện Legal Chunking cấp Điều, đính kèm Metadata và xây dựng bộ từ điển cứng `law_manifest.json`. | Kho dữ liệu vector sạch, Tập dữ liệu tổng hợp sinh bằng LLM mạnh, File `law_manifest.json`. |
| **Thành viên B** | **Retrieval Engineer** | Giai đoạn 3: Thiết lập cấu hình bộ tìm kiếm từ khóa BM25 tiếng Việt, cấu hình Vector Database local, xử lý Multi-Query, Query Expansion và triển khai thuật toán hợp nhất kết quả RRF Fusion. | Module Hybrid Retrieval đạt chỉ số Recall nội bộ tối ưu theo mục tiêu. |
| **Thành viên C** | **Reranker & Evaluation** | Giai đoạn 2 & Giai đoạn 4: Thiết lập bộ công cụ chấm điểm Benchmark nội bộ, triển khai cấu hình các mô hình Cross-Encoder local, xử lý Hard Negative Mining để tinh lọc kết quả tìm kiếm. | File `evaluation_report.md` cập nhật tiến độ liên tục, Tầng Reranker tối ưu. |
| **Thành viên D** | **LLM & Pipeline Engineer** | Giai đoạn 5, Giai đoạn 6 & Giai đoạn 7: Cài đặt vLLM/Ollama chạy local mô hình DeepSeek/Qwen, thiết kế System Prompt ép cấu trúc, xây dựng module Self-Verification và bộ lọc Regex hậu xử lý xuất file JSON chuẩn. | Pipeline chạy tự động hoàn chỉnh, File `results.json` và `submission.zip` chuẩn format. |

---

## V. CHIẾN LƯỢC PHÂN PHỐI NĂNG LỰC THEO THỜI GIAN GẤP

Trường hợp thời gian triển khai thực tế bị thắt chặt, nhóm sẽ thực hiện bám sát theo 3 mức độ ưu tiên để đảm bảo luôn có bài nộp chất lượng tối ưu nhất:

*   **MỨC ĐỘ 1 (BẮT BUỘC PHẢI HOÀN THÀNH - CHIẾM 70% ĐIỂM SỐ):**
    *   Hoàn thành việc Chia chunk dữ liệu theo cấp Điều luật (Legal Chunking).
    *   Xây dựng hệ thống Hybrid Retrieval cơ bản (BM25 + Dense Search bằng BGE-M3) kết hợp RRF.
    *   Thiết lập file từ điển cứng `law_manifest.json`.
    *   Viết Module Hậu xử lý bằng Regex để tự động điền các trường `relevant_docs` và `relevant_articles` từ văn bản text câu trả lời của LLM.
*   **MỨC ĐỘ 2 (TĂNG MẠNH ĐIỂM SỐ ĐỂ BỨT PHÁ TOP VÀO VÒNG TRONG):**
    *   Xây dựng hoàn chỉnh Bộ khung Đánh giá nội bộ (Evaluation Framework) để đo đạc chỉ số liên tục.
    *   Tích hợp Multi-Query và Metadata Filtering nhằm tối ưu hóa độ chính xác tầng tìm kiếm.
    *   Triển khai bộ kiểm định Self-Verification để lọc sạch lỗi ảo giác trước khi xuất kết quả.
*   **MỨC ĐỘ 3 (ĐUA TOP ĐẦU NẾU DƯ THỜI GIAN VÀ TÀI NGUYÊN PHẦN CỨNG):**
    *   Thực hiện Fine-tune mô hình Reranker bằng dữ liệu pháp lý chuyên sâu.
    *   Fine-tune mô hình Embedding tiếng Việt bằng kỹ thuật Hard Negative Mining.
    *   Chạy Benchmark so sánh liên tục giữa các cấu hình tham số khác nhau để tìm ra điểm cân bằng tối ưu nhất (Sweet spot) cho hệ thống.