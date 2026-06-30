# Bộ dữ liệu Văn bản Pháp luật Việt Nam — Tài liệu mô tả dữ liệu

Tài liệu này mô tả nguồn dữ liệu, cấu trúc/định dạng dữ liệu và hướng dẫn truy cập/sử dụng. Toàn bộ công việc chia thành **2 phần chính ngang hàng nhau**:

| Phần | Mục tiêu | Công cụ | Nơi chạy |
|------|----------|---------|----------|
| **PHẦN A — Thu thập & phân tích dữ liệu** | Crawl văn bản pháp luật từ web → JSON phân tầng + báo cáo thống kê/QA | `mass_crawler.py`, `analyze_law_data.py` | Máy local |
| **PHẦN B — Xây dựng Vector Database** | Chunk → Embedding → đẩy vào Qdrant để phục vụ tìm kiếm ngữ nghĩa / RAG | `build_law_2026_kaggle.ipynb` | Kaggle (GPU T4) |

```
Google Sheet (~612 URL)
        │  (chia theo đợt, mỗi đợt 1 batch)
        ▼
   urls_list.txt ──▶ mass_crawler.py ──▶ output_json/*.json ──▶ analyze_law_data.py ──▶ laws_overview_report.csv
   (đợt 5: 118 URL)   (crawl & bóc tách)   (dữ liệu phân tầng)     (thống kê & QA)        analysis_summary.json
                                                  │
                                                  ▼  (upload làm Kaggle Dataset)
                                  build_law_2026_kaggle.ipynb ──▶ Qdrant collection `law_2026`
                                  (chunk → embed → upsert)         + corpus_clean.json, law_manifest.json
```

---

# PHẦN A — Thu thập & phân tích dữ liệu

## A.1. Mô tả nguồn dữ liệu

| Hạng mục | Mô tả |
|----------|-------|
| **Nguồn gốc** | Cổng tra cứu **Thư Viện Pháp Luật** (`https://thuvienphapluat.vn`) |
| **Loại văn bản** | Luật, Bộ luật, Nghị định, Quyết định, Thông tư... của Quốc hội / Chính phủ Việt Nam |
| **Danh mục URL gốc** | Toàn bộ link được quản lý tập trung trên **Google Sheet**, tổng cộng **~612 URL** Thư Viện Pháp Luật: [Xem Google Sheet](https://docs.google.com/spreadsheets/d/1hw61KbTUpf9U_ptQMzGiu9HiHzplj1epJFaa2123heQ/edit?gid=0#gid=0) |
| **Cách triển khai** | Crawl được chạy **theo từng đợt (batch)** để giảm tải máy chủ nguồn và dễ kiểm soát chất lượng. Mỗi đợt copy một phần URL từ Google Sheet vào `urls_list.txt` rồi chạy crawler. |
| **Phạm vi của repo này** | Đây là dữ liệu của **đợt 5**: [urls_list.txt](urls_list.txt) chứa **118 URL**, và [output_json/](output_json/) là kết quả tương ứng (**115 file JSON**). Các đợt khác có file URL và output riêng. |
| **Ngôn ngữ** | Tiếng Việt |

### Quy trình lấy URL theo đợt
1. Mở Google Sheet danh mục (~612 URL).
2. Copy phần URL của đợt cần chạy vào file `urls_list.txt` (mỗi dòng một URL, dòng trống được tự bỏ qua).
3. Chạy `mass_crawler.py` → sinh ra `output_json/` cho đợt đó.

Ví dụ vài dòng trong `urls_list.txt` (đợt 5):
```
https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-45-2026-ND-CP-...-616621.aspx
https://thuvienphapluat.vn/van-ban/Dich-vu-phap-ly/Luat-cong-chung-2024-so-46-2024-QH15-524982.aspx
```

> **Lưu ý:** 118 URL đầu vào nhưng 115 file output — chênh lệch do một số URL crawl thất bại hoặc trùng tên file đầu ra. Dùng cột `Tổng Lỗi/Cảnh Báo QA` trong CSV để rà các file cần kiểm tra.

> **Lưu ý pháp lý/đạo đức khi crawl:** Crawler đã cấu hình `User-Agent` thật và **nghỉ giãn cách ngẫu nhiên 4–7 giây** giữa các request để tránh gây tải lên máy chủ nguồn. Dữ liệu chỉ dùng cho mục đích nghiên cứu, vui lòng tôn trọng điều khoản sử dụng của nguồn.

## A.2. Cấu trúc & định dạng dữ liệu

### A.2.1. Quy tắc đặt tên file output

`mass_crawler.py` tự suy ra tên file JSON từ URL (`extract_filename_from_url`):

| Trường hợp | Quy tắc | Ví dụ |
|------------|---------|-------|
| Có số hiệu dạng QH | Lấy cụm `số-năm-QH...` | `46-2024-QH15.json`, `49-2005-QH11.json` |
| Không có số hiệu QH | Lấy slug tên văn bản (đã bỏ ID rác cuối URL) | `Nghi-dinh-45-2026-ND-CP-...json`, `Luat-Hon-nhan-va-gia-dinh-2014.json` |

### A.2.2. Định dạng file văn bản (`output_json/*.json`)

Định dạng: **JSON, UTF-8, indent 4** (`ensure_ascii=False` — giữ nguyên tiếng Việt có dấu).

Cấu trúc **phân tầng 4 cấp**: `Chương → Điều → Khoản → Điểm`.

```jsonc
{
  "ten_luat": "Luật Các công cụ chuyển nhượng 2005 số 49/2005/QH11 áp dụng 2024",
  "so_hieu": "49/2005/QH11",
  "danh_sach_chuong": [
    {
      "id_chuong": "Chương I",
      "tieu_de_chuong": "NHỮNG QUY ĐỊNH CHUNG",
      "danh_sach_dieu": [
        {
          "id_dieu": "Điều 1",
          "tieu_de": "Phạm vi điều chỉnh",
          "noi_dung_chung": "Luật này điều chỉnh các quan hệ...",
          "khoan": [
            {
              "id_khoan": "1",
              "noi_dung_khoan": "Người ký phát, người phát hành được...",
              "diem": [
                { "id_diem": "a", "noi_dung": "..." }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Mô tả các trường:**

| Trường | Kiểu | Ý nghĩa |
|--------|------|---------|
| `ten_luat` | string | Tên đầy đủ của văn bản (lấy từ thẻ `<h1>`) |
| `so_hieu` | string | Số hiệu văn bản, ví dụ `49/2005/QH11` |
| `danh_sach_chuong[]` | array | Danh sách các Chương |
| `danh_sach_chuong[].id_chuong` | string | Mã chương, ví dụ `Chương I` (hoặc `Chương mở đầu` nếu văn bản không chia chương) |
| `danh_sach_chuong[].tieu_de_chuong` | string | Tiêu đề chương |
| `…danh_sach_dieu[].id_dieu` | string | Mã điều, ví dụ `Điều 1` |
| `…danh_sach_dieu[].tieu_de` | string | Tiêu đề điều |
| `…danh_sach_dieu[].noi_dung_chung` | string | Nội dung của Điều không nằm trong Khoản nào |
| `…khoan[].id_khoan` | string | Số khoản, ví dụ `"1"` |
| `…khoan[].noi_dung_khoan` | string | Nội dung khoản |
| `…diem[].id_diem` | string | Ký tự điểm, ví dụ `"a"`, `"b"`, `"đ"` |
| `…diem[].noi_dung` | string | Nội dung điểm |

> Điều không có khoản con sẽ có `"khoan": []` và toàn bộ nội dung nằm trong `noi_dung_chung`. Khoản không có điểm con sẽ có `"diem": []`.

### A.2.3. Định dạng báo cáo phân tích

#### a) `laws_overview_report.csv` — Bảng tổng hợp so sánh nhanh
CSV, UTF-8, 1 dòng / 1 văn bản. Các cột:

| Cột | Ý nghĩa |
|-----|---------|
| `Tên File` | Tên file JSON nguồn |
| `Số Hiệu Văn Bản` | Số hiệu |
| `Tổng Chương` / `Tổng Điều` / `Tổng Khoản` / `Tổng Điểm` | Đếm số phần tử mỗi cấp |
| `Tổng Ký Tự` | Tổng số ký tự nội dung |
| `Độ Dài TB Điều` | Số ký tự trung bình mỗi Điều |
| `Tổng Lỗi/Cảnh Báo QA` | Tổng số cảnh báo chất lượng (thiếu điều/khoản/điểm + lỗi cấu trúc + text rác) |

#### b) `analysis_summary.json` — Báo cáo chi tiết đầy đủ
JSON, UTF-8. Key là tên file, value là báo cáo phân tích sâu của từng văn bản:

```jsonc
{
  "49-2005-QH11.json": {
    "ten_luat": "...", "so_hieu": "...",
    "thong_ke_tong_quat": { "tong_chuong": .., "tong_dieu": .., "tong_khoan": .., "tong_diem": .., "do_dai_trung_binh_dieu": .. },
    "do_phuc_tap_ai":     { "khoan_tren_dieu": .., "diem_tren_khoan": .., "dieu_dai_nhat": {..}, "dieu_ngan_nhat": {..} },
    "dinh_nghia_phap_ly": { "so_luong_dieu_dinh_nghia": .., "danh_sach_dieu": [..] },
    "canh_bao_qa":        { "thieu_dieu": [..], "thieu_khoan": [..], "thieu_diem": [..], "loi_cau_truc": [..], "thong_ke_rac": {..} },
    "tu_khoa_pho_bien":   { "người lao động": .., "doanh nghiệp": .., "thuế": .. },
    "chi_tiet_tung_dieu": [ { "dieu": "Điều 1", "so_khoan": .., "so_diem": .., "co_noi_dung_chung": "✅", "do_dai": .. } ]
  }
}
```

Nhóm thông tin chính:
- **`thong_ke_tong_quat`**: số lượng chương/điều/khoản/điểm, tổng ký tự, độ dài trung bình.
- **`do_phuc_tap_ai`**: chỉ số độ phức tạp (khoản/điều, điểm/khoản, điều dài/ngắn nhất) — hữu ích để chia chunk khi xây RAG/embedding (Phần B).
- **`dinh_nghia_phap_ly`**: phát hiện các Điều mang tính định nghĩa ("là", "được hiểu là"...).
- **`canh_bao_qa`**: kiểm định chất lượng — phát hiện thiếu điều/khoản/điểm bị nhảy số, lỗi cấu trúc, text rác, dòng trùng lặp.
- **`tu_khoa_pho_bien`**: tần suất các từ khóa pháp lý quan trọng.

## A.3. Hướng dẫn chạy

### A.3.1. Yêu cầu môi trường
- Python 3.9+
- Cài thư viện phụ thuộc:

```bash
pip install -r requirements.txt
```

(`requests`, `beautifulsoup4` cho crawl; `pandas`, `tabulate` cho phân tích/hiển thị.)

### A.3.2. Bước 1 — Thu thập dữ liệu (`mass_crawler.py`)

1. Chuẩn bị file [urls_list.txt](urls_list.txt) (copy URL của đợt cần chạy từ Google Sheet).
2. Chạy crawler:

```bash
python mass_crawler.py
```

**Kết quả:** sinh ra thư mục `output_json/` chứa các file `.json` phân tầng (mỗi văn bản 1 file). Console in tiến trình từng URL, số Chương/Điều bóc tách được và tổng kết số file thành công.

Cấu hình (sửa trực tiếp đầu file nếu cần):
- `INPUT_TXT_FILE = "urls_list.txt"` — file danh sách URL.
- `OUTPUT_DIR = "output_json"` — thư mục xuất.

> Crawler nghỉ ngẫu nhiên 4–7 giây giữa các URL, nên thời gian chạy ≈ số URL × ~5 giây. Với 118 URL của đợt 5 mất khoảng 10–15 phút.

### A.3.3. Bước 2 — Phân tích & kiểm định chất lượng (`analyze_law_data.py`)

```bash
python analyze_law_data.py
```

Script đọc toàn bộ file JSON trong `output_json/` và xuất ra:
- **`laws_overview_report.csv`** — bảng tổng hợp để xem nhanh / mở bằng Excel.
- **`analysis_summary.json`** — báo cáo phân tích chi tiết từng văn bản.

Cấu hình:
- `INPUT_DIR = "output_json"`
- `OUTPUT_CSV_REPORT = "laws_overview_report.csv"`
- `OUTPUT_JSON_REPORT = "analysis_summary.json"`

### A.3.4. Sử dụng dữ liệu trong code

```python
import json

# Đọc một văn bản đã bóc tách
with open("output_json/49-2005-QH11.json", encoding="utf-8") as f:
    luat = json.load(f)

for chuong in luat["danh_sach_chuong"]:
    for dieu in chuong["danh_sach_dieu"]:
        print(dieu["id_dieu"], "-", dieu["tieu_de"])
        for khoan in dieu["khoan"]:
            print("  ", khoan["id_khoan"], khoan["noi_dung_khoan"][:80])
```

```python
# Đọc báo cáo tổng hợp bằng pandas
import pandas as pd
df = pd.read_csv("laws_overview_report.csv")
print(df.sort_values("Tổng Điều", ascending=False).head())
```

---

# PHẦN B — Xây dựng Vector Database (`build_law_2026_kaggle.ipynb`)

Notebook nhận đầu ra `output_json/` ở Phần A và thực hiện **3 việc trên Kaggle (GPU T4)**: **Chunk → Embed → Upsert vào Qdrant**, tạo nền tảng cho tìm kiếm ngữ nghĩa / RAG.

## B.1. Mục tiêu, đầu vào & đầu ra

| Hạng mục | Chi tiết |
|----------|----------|
| **Đầu vào** | Thư mục `output_json/` (các file đã parse ở Phần A), upload lên Kaggle làm **Dataset** (vd `law-output-json`) |
| **Embedding model** | `AITeamVN/Vietnamese_Embedding` (kiến trúc bge-m3), **1024 chiều**, `normalize_embeddings=True` |
| **Vector DB đích** | Qdrant Cloud, collection **`law_2026`**, độ đo khoảng cách **DOT** (vector đã chuẩn hoá) |
| **Đầu ra phụ** | `corpus_clean.json` (toàn bộ chunk), `law_manifest.json` (danh mục số hiệu), `doc_number_review.csv` (bảng rà số hiệu) — tải về từ `/kaggle/working` |

> **An toàn:** collection đích là `law_2026`. Point id = `uuid5(unique_article_id)` ⇒ chạy lại notebook **không nhân đôi** dữ liệu (idempotent upsert). Đặt `RECREATE = True` để xoá-tạo lại collection từ đầu (mặc định `False`).

## B.2. Chiến lược chunking & định dạng `corpus_clean.json`

Chunk theo đơn vị **Điều**:
- `text` = `"<tiêu đề Điều>\n<nội dung Điều (gộp Khoản/Điểm)>"`.
- Điều **ngắn** (≤ `MAX_ARTICLE_CHARS = 3500` ký tự) → **1 chunk**, `clause_num = None`.
- Điều **dài** → **tách theo Khoản** thành nhiều mảnh < ngưỡng (tránh embedding bị cắt cụt ở 2048 token). id có hậu tố `_K<số khoản>`; `article_id` vẫn giữ `"Điều N"` nên việc chấm recall theo (văn bản, Điều) không đổi.
- `doc_number` (số hiệu) suy theo thứ tự ưu tiên `so_hieu` → `ten_luat` → tên file, kèm cờ *confidence* (`high`/`medium`/`low`) để rà soát.

Định dạng mỗi chunk:
```jsonc
{
    "id": "45/2019/QH14_Điều 129",
    "text": "Bồi thường thiệt hại\n1. Người lao động làm hư hỏng dụng cụ, thiết bị hoặc có hành vi khác gây thiệt hại tài sản của người sử dụng lao động thì phải bồi thường theo quy định của pháp luật hoặc nội quy lao động của người sử dụng lao động. Trường hợp người lao động gây thiệt hại không nghiêm trọng do sơ suất với giá trị không quá 10 tháng lương tối thiểu vùng do Chính phủ công bố được áp dụng tại nơi người lao động làm việc thì người lao động phải bồi thường nhiều nhất là 03 tháng tiền lương và bị khấu trừ hằng tháng vào lương theo quy định tại khoản 3 Điều 102 của Bộ luật này .\n2. Người lao động làm mất dụng cụ, thiết bị, tài sản của người sử dụng lao động hoặc tài sản khác do người sử dụng lao động giao hoặc tiêu hao vật tư quá định mức cho phép thì phải bồi thường thiệt hại một phần hoặc toàn bộ theo thời giá thị trường hoặc nội quy lao động; trường hợp có hợp đồng trách nhiệm thì phải bồi thường theo hợp đồng trách nhiệm; trường hợp do thiên tai, hỏa hoạn, địch họa, dịch bệnh nguy hiểm, thảm họa, sự kiện xảy ra khách quan không thể lường trước được và không thể khắc phục được mặc dù đã áp dụng mọi biện pháp cần thiết và khả năng cho phép thì không phải bồi thường.",
    "metadata": {
      "chunk_id": "45/2019/QH14_Điều 129",
      "unique_article_id": "45/2019/QH14_Điều 129",
      "article_id": "Điều 129",
      "doc_id": "45/2019/QH14",
      "title": "Bộ luật lao động 2019 số 45/2019/QH14 áp dụng 2025",
      "context": {
        "part": null,
        "chapter": "Chương VIII KỶ LUẬT LAO ĐỘNG, TRÁCH NHIỆM VẬT CHẤT",
        "section": null
      },
      "clause_num": null,
      "original_content": ""
    }
  },
```

Payload đẩy vào Qdrant bao gồm: `chunk_id`, `unique_article_id`, `article_id`, `doc_id`, `title`, `text`, `context`, `clause_num`, `original_content`.

## B.3. Hướng dẫn chạy notebook trên Kaggle

**Chuẩn bị:**
1. Nén thư mục `output_json/` ở local → **upload làm Kaggle Dataset** (vd `law-output-json`).
2. Sửa `INPUT_DIR` ở **Cell 2 (Config)** cho khớp đường dẫn mount, vd `/kaggle/input/law-output-json/output_json`.
3. Khai báo 2 secret `QDRANT_URL` và `QDRANT_API_KEY` (xem chi tiết ở **B.3.1**).
4. Bật **GPU (T4)** trong Settings.

### B.3.1. Cập nhật `QDRANT_URL` & `QDRANT_API_KEY` vào Kaggle

> 🔑 **Lấy thông tin kết nối Qdrant tại file key:** https://drive.google.com/file/d/1KGUotNQ1MVZkJ0V9wGwazeM3M594snVD/view?usp=sharing
> File này chứa giá trị `QDRANT_URL` (endpoint cluster) và `QDRANT_API_KEY` (khóa truy cập).

**Các bước thêm secret trên Kaggle:**
1. Mở notebook trên Kaggle → menu **Add-ons → Secrets** (hoặc **Settings → Secrets**).
2. Bấm **Add secret**, tạo lần lượt 2 secret (Label phải **đúng tên**, phân biệt hoa thường):
   | Label (Key) | Value |
   |-------------|-------|
   | `QDRANT_URL` | Endpoint cluster, dạng `https://xxxx.cloud.qdrant.io:6333` (lấy từ file key) |
   | `QDRANT_API_KEY` | Khóa API Qdrant (lấy từ file key) |
3. Bật công tắc **Attach** cho cả 2 secret để notebook truy cập được.
4. Chạy lại **Cell 3** — notebook tự nạp secret qua `UserSecretsClient`:
   ```python
   from kaggle_secrets import UserSecretsClient
   sec = UserSecretsClient()
   os.environ["QDRANT_URL"]     = sec.get_secret("QDRANT_URL")
   os.environ["QDRANT_API_KEY"] = sec.get_secret("QDRANT_API_KEY")
   ```
   Nếu in ra `Secrets loaded từ Kaggle.` là thành công.

> ⚠️ **Bảo mật:** KHÔNG dán trực tiếp `QDRANT_URL`/`QDRANT_API_KEY` vào ô code rồi commit/chia sẻ notebook ở chế độ public — chỉ dùng cơ chế Secrets. Phần fallback gán cứng trong Cell 3 chỉ để chạy thử local và phải xoá trước khi chia sẻ.

**Chạy lần lượt các cell:**

| Cell | Việc làm |
|------|----------|
| 1 | Cài thư viện: `qdrant-client`, `sentence-transformers`, `python-dotenv`, `tqdm` |
| 2 | Config: `INPUT_DIR`, `COLLECTION_NAME`, `RECREATE`, model, `MAX_SEQ_LEN=2048`, `BATCH_SIZE=8`, `MAX_ARTICLE_CHARS=3500` |
| 3 | Nạp Qdrant secrets từ Kaggle |
| 4–6 | Định nghĩa hàm chunking, chạy chunk → `corpus_clean.json` + `manifest` + bảng rà số hiệu, kiểm tra mắt vài chunk |
| 7 | Kiểm tra GPU + nạp embedding model (chốt `max_seq_length` tránh OOM) |
| 8 | Embed toàn bộ chunk (`normalize_embeddings=True`) |
| 9 | Tạo collection `law_2026` (nếu chưa có) + upsert theo lô 256 điểm |
| 10 | Kiểm chứng: `points_count` + thử 1 truy vấn ngữ nghĩa |
| 11 | Lưu `corpus_clean.json` + `law_manifest.json` ra `/kaggle/working` để tải về |

> **Chống CUDA OOM trên T4 (14.5 GB):** model bge-m3 mặc định `max_seq_length=8192` gây nổ VRAM. Notebook chốt `MAX_SEQ_LEN=2048` + `BATCH_SIZE=8`. Nếu vẫn OOM, hạ `BATCH_SIZE` xuống 4 ở Cell 2, Restart kernel và chạy lại.

---

# Cấu trúc thư mục

```
prepare-data/
├── urls_list.txt              # PHẦN A — Danh sách URL đầu vào (đợt 5: 118 URL, copy từ Google Sheet ~612 URL)
├── mass_crawler.py            # PHẦN A — Bước 1: crawl + bóc tách → output_json/
├── output_json/               # PHẦN A — Dữ liệu văn bản phân tầng (115 file .json)
├── analyze_law_data.py        # PHẦN A — Bước 2: phân tích thống kê & QA
├── laws_overview_report.csv   # PHẦN A — Output: bảng tổng hợp
├── analysis_summary.json      # PHẦN A — Output: báo cáo chi tiết
├── requirements.txt           # PHẦN A — Thư viện phụ thuộc
├── build_law_2026_kaggle.ipynb# PHẦN B — Notebook chunk → embed → Qdrant (law_2026)
└── R2AIStage1DATA.json         # Bộ câu hỏi đánh giá (2000 câu, định dạng {id, question}) dùng để test truy vấn trên vector DB
```

---

# Lưu ý & giới hạn

- Dữ liệu phụ thuộc vào cấu trúc HTML của nguồn; văn bản có định dạng khác thường có thể bị bóc tách thiếu — hãy kiểm tra cột `Tổng Lỗi/Cảnh Báo QA` trong CSV và mục `canh_bao_qa` trong JSON để xác định file cần rà soát thủ công.
- Crawler tự động dừng khi gặp phần ký tên / bản tiếng Anh cuối văn bản ("Luật này được Quốc hội... thông qua", "Chủ tịch Quốc hội", "National Assembly", "Law on").
- Mỗi đợt crawl tạo ra một bộ `urls_list.txt` + `output_json/` riêng; repo này chứa dữ liệu **đợt 5**.
- File output trong `output_json/` có thể bị `.gitignore` loại trừ ở các dự án con (`backend/*.json`); ở thư mục này chúng được commit để phục vụ phân tích và Phần B.
```
