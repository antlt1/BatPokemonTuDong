import json
import time
import cv2
import numpy as np
import mss
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"

def screenshot_bgr():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = np.array(sct.grab(monitor))
    return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)

def test_hp():
    # Load config
    if not CONFIG_PATH.exists():
        print(f"❌ Không tìm thấy file config tại {CONFIG_PATH}")
        return
        
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    hp_roi = config.get("roi", {}).get("enemy_hp_bar", [520, 333, 247, 45])
    print(f"📌 ROI Máu Đang Dùng: {hp_roi}")
    print("⏳ Chuẩn bị chụp màn hình sau 2 giây... Hãy chắc chắn game đang hiển thị...")
    time.sleep(2)
    
    img = screenshot_bgr()
    if img is None:
        print("❌ Lỗi: Không chụp được màn hình!")
        return
        
    h_img, w_img = img.shape[:2]
    x, y, rw, rh = [int(v) for v in hp_roi]
    
    if x + rw > w_img or y + rh > h_img:
        print(f"❌ Lỗi: Vùng ROI {hp_roi} vượt quá kích thước màn hình ({w_img}x{h_img})!")
        return
        
    # Crop
    hp_region = img[y:y+rh, x:x+rw]
    
    # Save cropped debug image
    debug_path = ROOT / "debug_hp_captured.png"
    cv2.imwrite(str(debug_path), hp_region)
    print(f"💾 Đã lưu ảnh cắt vùng máu tại: {debug_path}")
    
    # Convert to HSV
    hsv = cv2.cvtColor(hp_region, cv2.COLOR_BGR2HSV)
    
    # Chúng ta sẽ thử nghiệm 3 mức Saturation (S) và Value (V) khác nhau:
    # 1. Thấp (40, 40) - Bị dính màu nền rừng cây
    # 2. Vừa (120, 120) - Bắt đầu lọc bớt màu nền
    # 3. Cao (180, 180) - Chỉ lấy màu neon cực sáng của thanh HP
    
    thresholds = [
        ("THẤP (S>=40, V>=40)", np.array([20, 40, 40])),
        ("TRUNG BÌNH (S>=120, V>=120)", np.array([20, 120, 120])),
        ("CAO (S>=180, V>=180) [Khuyên dùng]", np.array([20, 180, 180])),
    ]
    
    upper_green_yellow = np.array([85, 255, 255])
    
    print("\n--- SO SÁNH CÁC MỨC LỌC NHIỄU NỀN ---")
    for name, lower_limit in thresholds:
        mask = cv2.inRange(hsv, lower_limit, upper_green_yellow)
        green_yellow_count = np.sum(mask > 0)
        total_pixels = rw * rh
        ratio = green_yellow_count / total_pixels
        is_low = ratio < 0.05
        status_text = "🔴 MÁU YẾU" if is_low else "🟢 MÁU ĐẦY/TB"
        print(f"• {name}: {green_yellow_count:4d} px ({ratio*100:5.2f}%) -> Kết luận: {status_text}")

    # Vẽ phân tích chi tiết cho mức CAO (S>=180, V>=180) để xác định dòng thanh máu
    best_lower = np.array([20, 180, 180])
    mask_best = cv2.inRange(hsv, best_lower, upper_green_yellow)
    
    row_counts = []
    for r in range(rh):
        row_pixels = np.sum(mask_best[r, :] > 0)
        row_counts.append(row_pixels)
        
    print("\n--- PHÂN TÍCH THEO DÒNG DỌC VỚI BỘ LỌC CAO (LỌC NỀN) ---")
    detected_hp_rows = []
    for r, count in enumerate(row_counts):
        bar_visual = "#" * int(count / 10)
        print(f"Dòng {r:02d}: {count:3d} pixels | {bar_visual}")
        if count > (rw * 0.15): # Thanh máu dẹt hơn khi lọc sạch
            detected_hp_rows.append(r)
            
    if detected_hp_rows:
        ymin, ymax = min(detected_hp_rows), max(detected_hp_rows)
        print(f"\n💡 Đề xuất: Thanh máu thực tế nằm ở khoảng Dòng {ymin} đến {ymax} của ảnh cắt.")
        hp_strip = mask_best[ymin:ymax+1, :]
        green_yellow_count = np.sum(hp_strip > 0)
        total_pixels = rw * (ymax - ymin + 1)
        ratio = green_yellow_count / total_pixels
    else:
        print("\n⚠️ Không tự động phát hiện được thanh máu ở mức lọc cao (có thể do máu đã đỏ/cạn).")
        green_yellow_count = np.sum(mask_best > 0)
        total_pixels = rw * rh
        ratio = green_yellow_count / total_pixels
    
    print("\n--- KẾT QUẢ PHÂN TÍCH MỨC CAO (SAU KHI THU HẸP) ---")
    print(f"• Tổng số pixel trong vùng thanh máu: {total_pixels}")
    print(f"• Số pixel có màu Xanh/Vàng: {green_yellow_count}")
    print(f"• Tỉ lệ màu Xanh/Vàng: {ratio * 100:.2f}%")
    
    is_low = ratio < 0.10
    if is_low:
        print("🔴 Kết luận cuối cùng: MÁU YẾU (Low HP)")
    else:
        print("🟢 Kết luận cuối cùng: MÁU ĐẦY/TRUNG BÌNH (High/Med HP)")
        
if __name__ == "__main__":
    test_hp()
