# 🎒 Tab 4: Bag Scanner + 🎯 Tab 5: Auto Farm Config - Hướng Dẫn

## 📌 Tổng Quan

Bạn vừa có 2 tab mới để quản lý Pokemon và team farm:

### **Tab 4 - Bag Scanner (🎒)**
Quét **tất cả Pokemon trong túi đồ** (lên tới ~100 con), lưu vào `pokemon_bag_inventory.json`

### **Tab 5 - Auto Farm Config (⚙️🎯)**
Chọn **6 con từ Bag** để farm, lưu vào `team_farm.json`

---

## 🎯 Tab 4: Bag Scanner - Chi Tiết

### **Flow Quét**

1. **Tải/Dán ảnh túi đồ**
   - Click "📂 Mở ảnh" hoặc `Ctrl+V` (paste từ clipboard)
   - Ảnh sẽ hiển thị ở canvas bên trái

2. **Kéo ROI để quét tên Pokemon**
   - Click button "🎯 Kéo vùng 6 tên Pokemon"
   - Kéo bao quanh **cột tên của các con** (từ trên xuống dưới)
   - Hệ thống tự chia thành từng dòng → OCR tên mỗi con
   - Tối đa **~100 Pokemon** sẽ được chia tự động thành trang (Pagination)

3. **Kéo ROI để quét 4 Moves**
   - Chọn 1 Pokemon từ danh sách bên phải
   - Click "🎯 Kéo vùng 4 move"
   - Kéo bao quanh **bảng 4 move + PP** của con đó
   - Hệ thống tự chia thành 4 dòng → OCR move name + PP

4. **Sửa tay (nếu OCR lỗi)**
   - List bên phải cho phép chỉnh sửa tên Pokemon + moves
   - Nếu OCR bị lỗi, có thể xóa con sai hoặc edit lại

5. **Pagination**
   - Page 1 | Page 2 | Page 3...
   - Max 6 con/page (có thể config lại nếu cần)
   - Button "< Prev" | "Next >"

6. **Lưu**
   - Click "💾 Lưu JSON"
   - Kết quả: `src/config/pokemon_bag_inventory.json`

### **JSON Output Example** (pokemon_bag_inventory.json)
```json
[
  {
    "name": "Gyarados",
    "moves": [
      {"name": "Dragon Dance", "pp": "15/15"},
      {"name": "Ice Fang", "pp": "15/15"},
      {"name": "Crunch", "pp": "15/15"},
      {"name": "Waterfall", "pp": "15/20"}
    ]
  },
  {
    "name": "Spheal",
    "moves": [
      {"name": "Aurora Beam", "pp": "20/20"},
      ...
    ]
  }
]
```

---

## ⚙️ Tab 5: Auto Farm Config - Chi Tiết

### **Flow Chọn Team**

1. **Load Bag Inventory**
   - Tự động load danh sách từ `pokemon_bag_inventory.json`
   - Hiển thị list bên trái: "Gyarados (4 moves)", "Spheal (4 moves)", ...

2. **Chọn 1 Pokemon để thêm vào team**
   - Click 1 con từ list bên trái
   - Thông tin hiển thị: "Chọn: Gyarados (4 moves)"
   - Click button "➕ Add to Team"

3. **Team Farm Display** (bên phải)
   - Tối đa **6 slots** (như Party Scanner)
   - #1: 🔸 Gyarados
       - • Dragon Dance (15/15)
       - • Ice Fang (15/15)
       - • Crunch (15/15)
       - • Waterfall (15/20)
   - #2: 🔸 Spheal
       - ...
   - Có button "✕" để xóa con khỏi team

4. **Lưu Team Farm**
   - Click "💾 Lưu Team Farm"
   - Kết quả: `src/config/team_farm.json`
   - Hiển thị: "Team Farm (6/6): Gyarados, Spheal, ..."

### **JSON Output Example** (team_farm.json)
```json
[
  {
    "name": "Gyarados",
    "moves": [
      {"name": "Dragon Dance", "pp": "15/15"},
      {"name": "Ice Fang", "pp": "15/15"},
      {"name": "Crunch", "pp": "15/15"},
      {"name": "Waterfall", "pp": "15/20"}
    ]
  },
  {
    "name": "Spheal",
    "moves": [...]
  },
  ...
  (tối đa 6 con)
]
```

---

## 🔄 Integration với Mode 1 & 3

### **Mode 1 - Auto Catch** (phát triển sau)
```python
# run_pokemon_tool.py sẽ đọc
team_farm = load_json(ROOT / "src" / "config" / "team_farm.json")
# Sử dụng 6 con này để auto catch Pokemon
```

### **Mode 3 - Auto Farm** (hiện tại)
```python
# farm_battle.py sẽ đọc
team_farm = load_json(ROOT / "src" / "config" / "team_farm.json")
# Sử dụng 6 con này để farm tiền
```

---

## 📋 File Cấu Hình

- **`src/config/pokemon_bag_inventory.json`** - Danh sách ALL Pokemon trong túi (quét từ Tab 4)
- **`src/config/team_farm.json`** - Team 6 con để farm (chọn từ Tab 5)

---

## ⚡ Tips & Tricks

1. **OCR bị sai?**
   - Kiểm tra ảnh có sáng đủ không
   - Tesseract phải được cài đặt + PATH đúng

2. **Muốn thêm nhiều Pokemon cùng lúc?**
   - Scan nhiều lần, mỗi lần thêm một nhóm tên
   - Hệ thống sẽ auto đếm và phân trang

3. **Xóa Pokemon?**
   - Bên phải, click "✕" để xóa khỏi team
   - Click "🗑️ Xóa All" để clear toàn bộ

4. **Reload Bag?**
   - Click "🔄 Reload Bag" ở Tab 5 nếu file `pokemon_bag_inventory.json` bị thay đổi

---

## 🛠️ Cấu Trúc Code

```
src/team_builder/
├── bag_scanner_tab.py          # Tab 4 - Quét túi đồ
├── auto_farm_config_tab.py     # Tab 5 - Chọn team farm
└── party_scanner_tab.py        # Tab 3 cũ - Quét team party

src/tools/
└── modern_ui.py                # Giao diện chính (CustomTkinter)

src/config/
├── pokemon_bag_inventory.json  # Output Tab 4
├── team_farm.json              # Output Tab 5
├── team_party.json             # Output Tab 3
└── tool_config.json            # Config chung
```

---

## ✅ Checklist Để Test

- [ ] Mở Tab 4, paste ảnh túi đồ
- [ ] Kéo vùng tên → quét 3-5 con
- [ ] Kéo vùng move của 1 con → quét 4 moves
- [ ] Click "💾 Lưu JSON"
- [ ] Xem `pokemon_bag_inventory.json` tạo thành công
- [ ] Mở Tab 5, check list Pokemon load được
- [ ] Thêm 6 con vào team
- [ ] Lưu "💾 Lưu Team Farm"
- [ ] Xem `team_farm.json` tạo thành công

---

## 🤔 Hỏi Đáp

**Q: Tại sao phải scan bag trước?**  
A: Vì mỗi Pokemon có moves riêng → cần lưu cái data này → sau đó chọn 6 con từ list.

**Q: Có thể chỉnh sửa PP manually?**  
A: Hiện tại chưa → nhưng bạn có thể edit JSON trực tiếp.

**Q: Max bao nhiêu con trong bag?**  
A: Tối đa ~100 con (pagination sẽ tự chia thành 16-17 trang).

---

Đó! Bạn đã sẵn sàng để quét bag và chọn team farm rồi! 🚀
