import os
import re
import json
import csv
from collections import Counter

# Cấu hình đường dẫn
INPUT_DIR = "output_json"
OUTPUT_JSON_REPORT = "analysis_summary.json"
OUTPUT_CSV_REPORT = "laws_overview_report.csv"

# Các bộ từ vựng nhận diện cấu trúc và rác pháp lý
TRASH_KEYWORDS = ["xem thêm", "tải về", "english version", "related documents", "thuvienphapluat", "bản in"]
DEFINITIONAL_KEYWORDS = [r"\blà\b", r"\bđược hiểu là\b", r"\btrong luật này\b", r"\bquy định tại\b"]

# Bộ từ khóa phổ biến để thống kê
LEGAL_KEYWORDS = [
    "người lao động", "người sử dụng lao động", "doanh nghiệp", "thuế", 
    "trách nhiệm", "xử phạt", "cơ quan", "thủ tục", "điều kiện", "bảo hiểm"
]

def alphabet_to_index(char):
    """Chuyển đổi ký tự điểm thành chỉ mục số để kiểm tra nhảy bậc"""
    char = char.lower()
    alphabet_order = 'abcdefghijklmnopqrsštuvwxyz'
    if char == 'đ':
        return alphabet_order.index('d') + 0.5
    if char in alphabet_order:
        return alphabet_order.index(char)
    return -1

def analyze_single_law(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ten_luat = data.get("ten_luat", "")
    so_hieu = data.get("so_hieu", "")
    danh_sach_chuong = data.get("danh_sach_chuong", [])

    # Khởi tạo các biến đếm
    tong_chuong = len(danh_sach_chuong)
    tong_dieu = 0
    tong_khoan = 0
    tong_diem = 0
    
    dieu_khong_co_khoan = 0
    dieu_co_khoan = 0
    khoan_khong_co_diem = 0
    khoan_co_diem = 0
    tong_so_ky_tu = 0

    dieu_details = []
    dieu_numbers = []
    
    thieu_dieu = []
    thieu_khoan = []
    thieu_diem = []
    loi_cau_truc = []
    
    count_text_rac = 0
    count_trung_lap = 0
    count_dong_ngan = 0
    
    all_text_content = ""
    dieu_dinh_nghia_list = []
    
    max_len_dieu = 0
    max_len_dieu_id = ""
    min_len_dieu = float('inf')
    min_len_dieu_id = ""

    seen_lines = set()

    # VÒNG LẶP DUYỆT KHÉP KÍN ĐỂ TRÁNH SÓT ĐIỀU
    for chuong in danh_sach_chuong:
        tieu_de_chuong = chuong.get("tieu_de_chuong", "")
        cac_dieu_trong_chuong = chuong.get("danh_sach_dieu", [])
        
        if any(kw in tieu_de_chuong.lower() for kw in TRASH_KEYWORDS):
            count_text_rac += 1

        for dieu in cac_dieu_trong_chuong:
            tong_dieu += 1  
            dieu_id_str = dieu.get("id_dieu", "")
            
            # Tách số Điều chuẩn xác
            match_dieu_num = re.search(r"\d+", dieu_id_str)
            dieu_num = int(match_dieu_num.group()) if match_dieu_num else None
            if dieu_num:
                dieu_numbers.append(dieu_num)

            tieu_de = dieu.get("tieu_de") or ""
            noi_dung_chung = dieu.get("noi_dung_chung", "")
            khoan_list = dieu.get("khoan") or []
            if not isinstance(khoan_list, list):
                khoan_list = []
            
            dieu_text = f"{dieu_id_str} {tieu_de} {noi_dung_chung} " + " ".join([k.get("noi_dung_khoan", "") for k in khoan_list])
            dieu_len = len(dieu_text)
            tong_so_ky_tu += dieu_len
            all_text_content += " " + dieu_text.lower()

            if dieu_len > max_len_dieu:
                max_len_dieu = dieu_len
                max_len_dieu_id = dieu_id_str
            if dieu_len < min_len_dieu and dieu_len > 0:
                min_len_dieu = dieu_len
                min_len_dieu_id = dieu_id_str

            for chunk in [tieu_de, noi_dung_chung]:
                chunk_lower = chunk.lower()
                if any(kw in chunk_lower for kw in TRASH_KEYWORDS):
                    count_text_rac += 1
                if chunk and len(chunk) < 10:
                    count_dong_ngan += 1
                if chunk in seen_lines and chunk != "":
                    count_trung_lap += 1
                if chunk:
                    seen_lines.add(chunk)

            if any(re.search(pattern, dieu_text.lower()) for pattern in DEFINITIONAL_KEYWORDS) or "định nghĩa" in tieu_de.lower():
                dieu_dinh_nghia_list.append(dieu_id_str)

            num_khoan_in_dieu = len(khoan_list)
            num_diem_in_dieu = 0
            has_noi_dung_chung = "✅" if noi_dung_chung.strip() else "❌"

            if num_khoan_in_dieu == 0:
                dieu_khong_co_khoan += 1
                if dieu_len > 1000:
                    loi_cau_truc.append(f"{dieu_id_str}: Không có khoản nhưng độ dài bất thường ({dieu_len} ký tự).")
            else:
                dieu_co_khoan += 1

            khoan_numbers = []
            for k in khoan_list:
                tong_khoan += 1
                id_khoan = k.get("id_khoan", "")
                noi_dung_khoan = k.get("noi_dung_khoan", "")
                diem_list = k.get("diem") or []
                if not isinstance(diem_list, list):
                    diem_list = []
                num_diem = len(diem_list)
                num_diem_in_dieu += num_diem
                tong_diem += num_diem

                if id_khoan.isdigit():
                    khoan_numbers.append(int(id_khoan))

                if num_diem == 0:
                    khoan_khong_co_diem += 1
                else:
                    khoan_co_diem += 1

                if num_diem > 0:
                    diem_chars = [p.get("id_diem", "").lower() for p in diem_list if p.get("id_diem", "")]
                    for i in range(1, len(diem_chars)):
                        prev_idx = alphabet_to_index(diem_chars[i-1])
                        curr_idx = alphabet_to_index(diem_chars[i])
                        if curr_idx != -1 and prev_idx != -1 and (curr_idx - prev_idx) > 1.5:
                            thieu_diem.append(f"{dieu_id_str} - Khoản {id_khoan}: Nghi vấn thiếu điểm giữa điểm '{diem_chars[i-1]})' and '{diem_chars[i]})'")

            if khoan_numbers:
                khoan_numbers.sort()
                for i in range(len(khoan_numbers) - 1):
                    if khoan_numbers[i+1] - khoan_numbers[i] > 1:
                        thieu_khoan.append(f"{dieu_id_str}: Thiếu khoản giữa Khoản {khoan_numbers[i]} và Khoản {khoan_numbers[i+1]}")

            dieu_details.append({
                "dieu": dieu_id_str,
                "so_khoan": num_khoan_in_dieu,
                "so_diem": num_diem_in_dieu,
                "co_noi_dung_chung": has_noi_dung_chung,
                "do_dai": dieu_len
            })

    # QA Văn bản nâng cao
    if dieu_numbers:
        unique_dieu_numbers = sorted(list(set(dieu_numbers)))
        full_range = set(range(unique_dieu_numbers[0], unique_dieu_numbers[-1] + 1))
        missing_set = full_range - set(unique_dieu_numbers)
        thieu_dieu = [f"Điều {m}" for m in sorted(list(missing_set))]

    # Thống kê tần suất Từ khóa pháp lý
    keyword_trends = {}
    for kw in LEGAL_KEYWORDS:
        matches = re.findall(r'\b' + re.escape(kw) + r'\b', all_text_content)
        keyword_trends[kw] = len(matches)

    # Đóng gói kết quả tính toán chỉ số trung bình (AI Complexity)
    do_dai_trung_binh_dieu = round(tong_so_ky_tu / tong_dieu, 2) if tong_dieu > 0 else 0
    khoan_tren_dieu = round(tong_khoan / tong_dieu, 2) if tong_dieu > 0 else 0
    diem_tren_khoan = round(tong_diem / tong_khoan, 2) if tong_khoan > 0 else 0

    # KHỐI ĐÓNG GÓI DICTIONARY ĐẦU RA (BỊ THIẾU Ở CODE CŨ CỦA BẠN)
    analysis_res = {
        "ten_luat": ten_luat,
        "so_hieu": so_hieu,
        "thong_ke_tong_quat": {
            "tong_chuong": tong_chuong,
            "tong_dieu": tong_dieu,
            "tong_khoan": tong_khoan,
            "tong_diem": tong_diem,
            "dieu_khong_co_khoan": dieu_khong_co_khoan,
            "dieu_co_khoan": dieu_co_khoan,
            "khoan_khong_co_diem": khoan_khong_co_diem,
            "khoan_co_diem": khoan_co_diem,
            "tong_so_ky_tu": tong_so_ky_tu,
            "do_dai_trung_binh_dieu": do_dai_trung_binh_dieu
        },
        "do_phuc_tap_ai": {
            "khoan_tren_dieu": khoan_tren_dieu,
            "diem_tren_khoan": diem_tren_khoan,
            "dieu_dai_nhat": {"id": max_len_dieu_id, "ky_tu": max_len_dieu },
            "dieu_ngan_nhat": {"id": min_len_dieu_id, "ky_tu": min_len_dieu if min_len_dieu != float('inf') else 0 }
        },
        "dinh_nghia_phap_ly": {
            "so_luong_dieu_dinh_nghia": len(dieu_dinh_nghia_list),
            "danh_sach_dieu": dieu_dinh_nghia_list
        },
        "canh_bao_qa": {
            "thieu_dieu": thieu_dieu,
            "thieu_khoan": thieu_khoan,
            "thieu_diem": thieu_diem,
            "loi_cau_truc": loi_cau_truc,
            "thong_ke_rac": {
                "text_rac": count_text_rac,
                "trung_lap": count_trung_lap,
                "dong_cuc_ngan": count_dong_ngan
            }
        },
        "tu_khoa_pho_bien": keyword_trends,
        "chi_tiet_tung_dieu": dieu_details
    }
    return analysis_res

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"[!] Thư mục chứa file crawl '{INPUT_DIR}' không tồn tại.")
        return

    json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
    if not json_files:
        print(f"[!] Không tìm thấy file JSON nào trong thư mục '{INPUT_DIR}'.")
        return  

    print(f"[*] Đang thực hiện phân tích sâu dữ liệu trên {len(json_files)} văn bản luật...")
    
    all_summaries = {}
    csv_rows = []

    for file_name in json_files:
        file_path = os.path.join(INPUT_DIR, file_name)
        try:
            law_report = analyze_single_law(file_path)
            all_summaries[file_name] = law_report
            
            stq = law_report["thong_ke_tong_quat"]
            cb = law_report["canh_bao_qa"]
            tong_loi_he_thong = len(cb["thieu_dieu"]) + len(cb["thieu_khoan"]) + len(cb["thieu_diem"]) + len(cb["loi_cau_truc"]) + cb["thong_ke_rac"]["text_rac"]
            
            csv_rows.append({
                "Tên File": file_name,
                "Số Hiệu Văn Bản": law_report["so_hieu"],
                "Tổng Chương": stq["tong_chuong"],
                "Tổng Điều": stq["tong_dieu"],
                "Tổng Khoản": stq["tong_khoan"],
                "Tổng Điểm": stq["tong_diem"],
                "Tổng Ký Tự": stq["tong_so_ky_tu"],
                "Độ Dài TB Điều": stq["do_dai_trung_binh_dieu"],
                "Tổng Lỗi/Cảnh Báo QA": tong_loi_he_thong
            })
        except Exception as e:
            print(f"    [!] Gặp lỗi khi phân tích file: {file_name}. Lỗi: {str(e)}")

    # 1. Ghi file JSON Summary lớn chứa tất cả các văn bản
    with open(OUTPUT_JSON_REPORT, "w", encoding="utf-8") as f_json:
        json.dump(all_summaries, f_json, ensure_ascii=False, indent=4)
    print(f"[+] Đã xuất file JSON báo cáo chi tiết: {OUTPUT_JSON_REPORT}")

    # 2. Ghi file CSV Tổng hợp để quan sát nhanh cấu trúc dữ liệu
    csv_fields = ["Tên File", "Số Hiệu Văn Bản", "Tổng Chương", "Tổng Điều", "Tổng Khoản", "Tổng Điểm", "Tổng Ký Tự", "Độ Dài TB Điều", "Tổng Lỗi/Cảnh Báo QA"]
    with open(OUTPUT_CSV_REPORT, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[+] Đã xuất file CSV tổng hợp so sánh: {OUTPUT_CSV_REPORT}")
    print("\n=== HOÀN THÀNH QUÁ TRÌNH KIỂM ĐỊNH CHẤT LƯỢNG LUẬT ===")

if __name__ == "__main__":
    main()