# 🎮 PokemonPRO GUI - Hướng dẫn sử dụng

## 🚀 Khởi động

### Cách 1: Chạy batch file (Easiest)
- Nhấp đôi vào **`run_gui.bat`**
- Giao diện sẽ mở trong vòng 2-3 giây

### Cách 2: Chạy qua Terminal
```bash
python launch_gui.py
```

---

## 🎯 Cấu trúc Giao diện

### Sidebar (Trái) - Navigation
- 📊 **Dashboard** - Điều khiển Auto Farm, xem log realtime
- 👥 **Team Builder** - Xây dựng team 6 Pokemon (sắp tới)
- 📐 **Calibrate ROI** - Hiệu chỉnh vùng nhận dạng (sắp tới)
- ⚙️ **Settings** - Cấu hình tool (sắp tới)

### Main Content (Phải) - Tab Content
- Hiển thị nội dung tab được chọn
- Giao diện Dark Mode, thiết kế tối ưu

---

## 💡 Các tính năng chính

### 1️⃣ Dashboard - Auto Farm Control
**Tính năng:**
- 🟢 **Status Indicator** - Hiển thị trạng thái (Running/Stopped)
- ▶️ **START button** - Bắt đầu Auto Farm
- ⏹️ **STOP button** - Dừng Auto Farm
- 📝 **Live Log** - Xem log realtime trong GUI (thay vì CMD)

**Hotkey:**
- **Alt+F8** - Toggle Start/Stop (có thể dùng khi đang chơi game)

**Luồng làm việc:**
```
1. Bấm "▶️ START" hoặc "Alt+F8" 
   → Tool khởi động mode Auto Farm
   → Chạy trong background thread (không làm UI đơ)
   
2. Xem log realtime trong khung "📝 Live Log"
   → Tự động cuộn xuống để xem log mới nhất
   
3. Bấm "⏹️ STOP" hoặc "Alt+F8" 
   → Tool dừng gracefully
   → Status chuyển về 🔴 Stopped
```

---

## 🔧 Threading - Cách hoạt động

**Problem:** Nếu Auto Farm chạy trên thread chính, UI sẽ bị đơ (Freeze)

**Solution:** Dùng Python threading
- Auto Farm chạy trên **background thread** (worker thread)
- UI chạy trên **main thread** (responsive)
- Log được gửi qua **queue** để tránh race condition

```
┌─────────────────────────────────────┐
│ Main Thread (UI Responsive)         │
│ - Window events                     │
│ - Button clicks                     │
│ - Display updates                   │
└─────────────────────────────────────┘
          ↓        ↑
      Log Queue (Thread-safe)
          ↓        ↑
┌─────────────────────────────────────┐
│ Background Thread (Worker)          │
│ - Run auto farm logic               │
│ - Send logs via queue               │
│ - Run until stop signal received    │
└─────────────────────────────────────┘
```

---

## 📋 Log Display

**Tính năng:**
- ✅ Auto-scroll đến dòng mới nhất
- 🎨 Font: Courier (đẹp hơn terminal)
- 🟢 Text color: Green (dễ nhìn trên background đen)
- 📅 Timestamp: HH:MM:SS tự động thêm vào mỗi dòng
- 💾 Lưu vào file: `src/runtime/feedback_log.txt`

**Ví dụ log:**
```
[14:30:25] ✅ Auto Farm started!
[14:30:25] 🎮 Farming mode activated. Press Alt+F8 to stop.
[14:30:26] 🎯 Scanned screen - no battle yet
[14:30:28] 🎯 Scanned screen - no battle yet
[14:30:30] ⚔️ Battle detected! Enemy: Persian
[14:30:32] 🔄 My Pokemon: Gardevoir | Enemy: Persian
[14:30:33] 💫 Scanning moves...
```

---

## 🎛️ Status Indicator

**Trạng thái:**
- 🟢 **Running** - Green - Tool đang chạy
- 🔴 **Stopped** - Red - Tool không chạy

---

## ⚠️ Lưu ý quan trọng

1. **Hotkey Alt+F8 global** - Hoạt động ngay cả khi game đang focus
   - Dù bạn đang chơi game, bấm Alt+F8 vẫn work
   - Cẩn thận đừng bấm nhầm!

2. **Background thread graceful shutdown**
   - Bấm Stop sẽ gửi signal, thread sẽ tắt an toàn
   - Không hard-kill, nên không bị crash/corrupt data

3. **Log file**
   - Logs cũng được lưu vào `src/runtime/feedback_log.txt`
   - Dù UI bị đóng, log vẫn còn lại để debug

4. **Config loading**
   - Config được load từ `src/config/tool_config.json` lúc khởi động
   - Thay đổi config cần restart GUI

---

## 🔜 Tính năng sắp tới (Phase 2)

### Team Builder Tab
- 📸 Load team từ screenshots
- ✏️ OCR Pokemon name + 4 moves
- 🛠️ Edit manually nếu cần
- 💾 Save team vào JSON

### Calibrate ROI Tab
- 🖱️ Drag để adjust vùng nhận dạng
- 📷 Preview screenshot game
- 🎯 Save ROI positions vào config

### Settings Tab
- ⚙️ Adjust timing delays
- 🎨 UI themes
- 📊 Debug options
- 🔊 Audio settings

---

## 🐛 Troubleshooting

**Q: GUI không mở được?**
- A: Kiểm tra CMD log - có error gì không?
- Đảm bảo CustomTkinter đã cài: `pip install customtkinter`

**Q: Alt+F8 hotkey không work?**
- A: Chạy CMD với admin rights, hoặc check firewall
- Một số keyboard layout có thể không support Alt+F8

**Q: Sao log không cập nhật?**
- A: Check xem log queue có bị stuck không (console không hang)
- Logs mỗi 100ms được update 1 lần

**Q: Muốn xem lại các logs cũ?**
- A: Mở file `src/runtime/feedback_log.txt`

---

## 📞 Support

Nếu có vấn đề, kiểm tra:
1. Console output (error messages)
2. `src/runtime/feedback_log.txt` (logs lưu trữ)
3. Tool config: `src/config/tool_config.json`

---

**Enjoy your PokemonPRO farming! 🎮✨**
