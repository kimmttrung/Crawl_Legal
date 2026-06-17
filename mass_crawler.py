import os
import re
import time
import random
import json
import requests
from bs4 import BeautifulSoup

# Cấu hình môi trường và thư mục lưu kết quả
INPUT_TXT_FILE = "urls_list.txt"
OUTPUT_DIR = "output_json"
os.makedirs(OUTPUT_DIR, exist_ok=True)

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}

def extract_filename_from_url(url):
    """
    Xử lý chuỗi để lấy Số hiệu văn bản hoặc Tên bộ luật làm tên file JSON
    - Trường hợp 1: Có số hiệu rõ ràng -> 59-2020-QH14.json
    - Trường hợp 2: Không số hiệu (chỉ có chữ + năm) -> Bo-Luat-lao-dong-2019.json
    """
    # Làm sạch URL lấy phần chuỗi text cuối cùng, bỏ đuôi .aspx
    url_clean = url.split('/')[-1].replace('.aspx', '')
    
    # Tách bỏ ID số cuối cùng của Thư Viện Pháp Luật (ví dụ: -333670 hoặc -427301)
    parts = url_clean.split('-')
    if parts[-1].isdigit() and len(parts) > 1:
        parts = parts[:-1] # Bỏ số ID rác ở cuối
    
    name_without_id = "-".join(parts)

    # Thử tìm cụm dạng số-hiệu-QH bằng Regex từ chuỗi đã làm sạch
    match = re.search(r"(\d+-\d+-QH\d+)", name_without_id, re.IGNORECASE)
    if match:
        return f"{match.group(1).upper()}.json"
    
    # Nếu không có số hiệu dạng QH, lấy luôn tên bộ luật sạch đã bỏ ID làm tên file
    return f"{name_without_id}.json"

def crawl_and_parse_to_json(url, output_filename):
    print(f"[*] Đang xử lý: {url}")
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding

        if response.status_code != 200:
            print(f"    [!] Thất bại. Mã phản hồi của trang web: {response.status_code}")
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Trích xuất Tên luật từ thẻ H1
        h1_title = soup.find("h1")
        ten_luat = h1_title.get_text(strip=True) if h1_title else "Văn bản Pháp Luật"
        
        # 2. Tìm số hiệu thực tế của luật hiển thị trên website để đưa vào nội dung JSON
        so_hieu_luat = ""
        # Thử tìm số hiệu dựa trên định dạng file JSON tên số hiệu trước
        match_sh_file = re.search(r"(\d+/\d+/QH\d+)", output_filename.replace('-', '/'))
        if match_sh_file:
            so_hieu_luat = match_sh_file.group(1)
        else:
            # Nếu tên file là chữ, quét số hiệu từ văn bản thô (ví dụ: "Số: 59/2020/QH14" hoặc "Số hiệu: ...")
            match_sh_text = re.search(r"Số\s*(?:hiệu)?\s*:\s*([\w/|-]+)", response.text, re.IGNORECASE)
            if match_sh_text:
                so_hieu_luat = match_sh_text.group(1).strip()
            else:
                so_hieu_luat = output_filename.replace('.json', '') # Dự phòng bằng tên file

        # Định vị vùng dữ liệu cốt lõi
        main_content = soup.find("div", id="content1") or soup.find("div", class_="content-html")
        if not main_content:
            main_content = soup.find("body")

        for trash in main_content(["script", "style", "iframe", "header", "footer"]):
            trash.decompose()

        # Ép phẳng và gom dòng chữ bị ngắt bậy
        paragraphs = main_content.find_all(['p', 'div'])
        raw_lines = []
        for p in paragraphs:
            if p.name == 'div' and p.find('p'): 
                continue 
            text = p.get_text(" ", strip=True)
            text = re.sub(r'\s+', ' ', text) 
            if text and len(text) > 2:
                raw_lines.append(text)

        clean_lines = []
        for line in raw_lines:
            if not clean_lines or line != clean_lines[-1]:
                clean_lines.append(line)

        # Cấu trúc cây JSON đích
        luat_json = {
            "ten_luat": ten_luat,
            "so_hieu": so_hieu_luat,
            "danh_sach_dieu": []
        }

        # current_chuong = None
        current_dieu = None
        current_khoan = None
        start_parsing = False

        # Cấu trúc Regex nhận diện chuẩn xác đầu dòng
        # regex_chuong = re.compile(
        #     r"^Chương\s+([IVXLCDM]+)\.?\s*(.*)$",
        #     re.IGNORECASE
        # )
        regex_dieu = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$", re.IGNORECASE)
        regex_khoan = re.compile(r"^(\d+)\.\s*(.*)$")
        regex_diem = re.compile(r"^([a-zđ])\)\s*(.*)$", re.IGNORECASE)

        for line in clean_lines:
            # PHANH TỰ ĐỘNG: Ngắt ngay lập tức khi hết phần Tiếng Việt để tránh cào trúng tiếng Anh / mục lục rác
            if "CHỦ TỊCH QUỐC HỘI" in line or "NATIONAL ASSEMBLY" in line or "LAW ON" in line:
                break

            if line.startswith("Điều 1."):
                start_parsing = True

            if not start_parsing:
                continue

            # 1. Nhận diện ĐIỀU
            match_dieu = regex_dieu.match(line)
            if match_dieu and len(line) < 150:
                current_dieu = {
                    "id_dieu": f"Điều {match_dieu.group(1)}",
                    "tieu_de": match_dieu.group(2).strip(),
                    "noi_dung_chung": "",
                    "khoan": []
                }
                luat_json["danh_sach_dieu"].append(current_dieu)
                current_khoan = None 
                continue

            if not current_dieu:
                continue

            # 2. Nhận diện KHOẢN
            match_khoan = regex_khoan.match(line)
            if match_khoan:
                current_khoan = {
                    "id_khoan": match_khoan.group(1),
                    "noi_dung_khoan": match_khoan.group(2).strip(),
                    "diem": []
                }
                current_dieu["khoan"].append(current_khoan)
                continue

            # 3. Nhận diện ĐIỂM
            match_diem = regex_diem.match(line)
            if match_diem and current_khoan:
                current_khoan["diem"].append({
                    "id_diem": match_diem.group(1),
                    "noi_dung": match_diem.group(2).strip()
                })
                continue

            # 4. CỘNG DỒN NỘI DUNG CHỐNG NHIỄU TRÍCH DẪN CHÉO
            if current_khoan:
                current_khoan["noi_dung_khoan"] += " " + line
            else:
                if current_dieu["noi_dung_chung"]:
                    current_dieu["noi_dung_chung"] += " " + line
                else:
                    current_dieu["noi_dung_chung"] = line

        # Dọn dẹp khoảng trắng thừa lần cuối
        for d in luat_json["danh_sach_dieu"]:
            d["noi_dung_chung"] = re.sub(r'\s+', ' ', d["noi_dung_chung"]).strip()
            for k in d["khoan"]:
                k["noi_dung_khoan"] = re.sub(r'\s+', ' ', k["noi_dung_khoan"]).strip()

        # Lưu file JSON vào thư mục chỉ định
        full_output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(full_output_path, "w", encoding="utf-8") as f:
            json.dump(luat_json, f, ensure_ascii=False, indent=4)
            
        print(f"    [+] Xuất file thành công -> {full_output_path} ({len(luat_json['danh_sach_dieu'])} Điều)")
        return True

    except Exception as e:
        print(f"    [!] Lỗi phát sinh khi xử lý URL này: {str(e)}")
        return False

# ==============================================================================
# HÀM ĐIỀU HƯỚNG VÒNG LẶP CHẠY DANH SÁCH
# ==============================================================================
if __name__ == "__main__":
    if not os.path.exists(INPUT_TXT_FILE):
        print(f"[!] Lỗi: Vui lòng tạo file '{INPUT_TXT_FILE}' và nhập danh sách URL vào trước.")
        exit()

    with open(INPUT_TXT_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"[+] Tìm thấy {len(urls)} URL trong danh sách chuẩn bị xử lý.")
    print("-" * 60)

    success_count = 0
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] Cào tiến trình...")
        
        # Tự động tính toán tên file đầu ra từ cấu trúc URL (Số hiệu hoặc tên bộ luật)
        json_filename = extract_filename_from_url(url)
        
        # Chạy hàm xử lý cốt lõi
        success = crawl_and_parse_to_json(url, json_filename)
        if success:
            success_count += 1
            
        # CHIẾN LƯỢC RATE LIMITING: Nghỉ ngẫu nhiên giữa các URL để tránh bị quét thiết bị
        if idx < len(urls):
            sleep_time = random.uniform(4.0, 7.0)
            print(f"    [*] Nghỉ giãn cách an toàn {sleep_time:.2f} giây trước link tiếp theo...")
            time.sleep(sleep_time)

    print("\n" + "="*50)
    print(f"[+] ĐÃ HOÀN THÀNH TOÀN BỘ DANH SÁCH!")
    print(f"    - Hoàn thành xuất sắc: {success_count}/{len(urls)} file JSON.")
    print(f"    - Toàn bộ kết quả nằm trong thư mục: {os.path.abspath(OUTPUT_DIR)}")
    print("="*50)