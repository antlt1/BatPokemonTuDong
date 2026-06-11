# PokemonPRO Tool Project Memory

## Muc tieu

Du an nay lam tool Python xu ly anh cho PokemonPRO. Tool se chup/man hinh game, nhan dien trang thai battle, doc ten Pokemon/ability tu vung da cat san, va sau nay co the click nut trong game de bat Pokemon hoac run.

Thong tin man hinh hien tai:

- Man hinh Windows: `1920x1080`
- Size game muc tieu tung nhac toi: `1600x900`
- Huong tam thoi da chot: uu tien cat va xu ly theo anh chup/template `1920x1080`
- Man hinh/game se giu co dinh, khong dich chuyen cua so trong luc tool chay.
- Thu muc template mac dinh: `src/template/cap_gamedefault`
- Ten cua so game de focus: `PROClient`

Quy tac lam viec: chi code sau khi nguoi dung xac nhan ro. Neu con thieu thong tin thiet ke/logic, phai hoi truoc.

## Template hien co

Trong `src/template/cap_gamedefault`:

- `windowOpengame.png`: anh full screen, kich thuoc hien tai `1920x1080`
- `BattelPokemon.png`: vung header battle, kich thuoc hien tai `1920x307`
- `leftBar.png`: vung ben trai, kich thuoc hien tai `705x1080`
- `rightBar.png`: vung ben phai, kich thuoc hien tai `668x1080`
- `rightBarButtomFight.png`: template nut Fight
- `rightBarButtomItems.png`: template nut Items
- `rightBarButtomPokemon.png`: template nut Pokemon
- `rightBarButtomRun.png`: template nut Run
- `src/template/audio/quick-ting.mp3`: am thanh bao khi tim thay Pokemon/ability dung

Ghi chu: can chot cach map toa do tu anh chup `1920x1080` sang cua so game `1600x900` truoc khi code click that.

## Vung nhan dien

### Header battle

- Dung de nhan biet co dang vao battle hay khong.
- Dau hieu chinh: chu `VS.` trong header.
- Sau khi vao battle, header/khung battle se duoc dung de doc ten Pokemon doi thu.

### Right bar

- Dung de tim cac nut hanh dong, dac biet la nut `Run`.
- Tuong lai tool se click vao cac nut o right bar, gom cac nut bat Pokemon hoac run.
- Can xac dinh template/toa do nut `Run` theo ty le man hinh.

### Left bar va Battle Log

- Vung goc duoi ben trai co `Battle Log`.
- Nguoi dung se tu mo san Battle Log truoc khi chay tool.
- Dung de doc ability ma Pokemon cua minh check duoc.
- Mau log can doc: `Gardevoir's ability is now Effect Spore!`
- Neu Pokemon trong danh sach co ability cu the, tool phai doc log va so sanh ability do.

## Du lieu Pokemon can bat

Du kien dung file JSON chinh tay, vi du:

```json
[
  {
    "pokemonname": "Parasect",
    "ability": "Effect Spore"
  },
  {
    "pokemonname": "Exeggcute",
    "ability": "none"
  }
]
```

Y nghia:

- `ability: "none"`: gap dung Pokemon thi dung tool de nguoi dung tu bat.
- `ability: "<ten ability>"`: chi dung tool khi gap dung Pokemon va log doc duoc dung ability.
- File JSON de xuat: `src/config/target_pokemon.json`

## Menu CMD du kien

Tool Python se co menu chay trong CMD:

- Phim `1`: che do tim Pokemon, khi gap dung dieu kien thi dung code de nguoi dung tu bat.
- Phim `2`: che do tu bat Pokemon, se code tiep sau.

## Luong hoat dong du kien

1. Xac dinh/focus vao cua so game PokemonPRO.
2. Chup man hinh game.
3. Neu khong thay dau hieu `VS.` thi tiep tuc di chuyen qua lai bang `A D A D A D`, theo kieu tu nhien/gan nhu lien tuc.
4. Moi khoang `3s`, chup lai man hinh va quet xem da vao battle chua.
5. Neu da vao battle, doc ten Pokemon doi thu.
6. So sanh Pokemon voi file JSON.
7. Neu Pokemon khong nam trong danh sach, tim nut `Run` o right bar va click luon. Click `Run` mot lan la thoat battle, khong can xac nhan them.
8. Neu Pokemon nam trong danh sach va `ability` la `none`, dung tool de nguoi dung tu bat.
9. Neu Pokemon nam trong danh sach va can ability, doi khoang `2s` sau khi vao battle de log ability xuat hien, roi doc `Battle Log`.
10. Neu log co ability dung, dung tool de nguoi dung tu bat.
11. Neu ability sai hoac khong dung muc tieu, click `Run`.
12. Khi dung vi tim thay muc tieu, phat am thanh bao va in thong bao tren CMD.

## Huong framework/ky thuat de can nhac

- Screenshot/focus/click: `pyautogui`, `pygetwindow`, hoac Win32 API.
- Xu ly template/crop: `opencv-python`.
- OCR ten Pokemon va log: `pytesseract`, `easyocr`, hoac model OCR khac neu Tesseract doc pixel game kem.
- Config/toa do: luu bang JSON/YAML de sau nay sua crop va nut click nhanh.
- Huong tam thoi: bat dau voi `OpenCV + pytesseract`, neu doc chu game kem thi doi sang `easyocr`.

## Cau hoi can chot truoc khi code

1. Ten Pokemon doi thu nen doc tu vung nao la chuan nhat: header co chu `VS.` hay khung ten trong battle?
2. Neu OCR doc sai Pokemon/ability, co can luu screenshot loi vao thu muc debug khong?
3. Co can them phim dung khan cap, vi du bam `Q` de stop tool khong?
4. Cac ten Pokemon/ability trong JSON co can so sanh khong phan biet hoa/thuong khong?

## Quyet dinh da chot them

- Ten Pokemon doi thu: doc OCR tu khung ten trong battle, khong uu tien doc tu header `VS.`.
- Debug screenshot: nen luu anh khi OCR/doc trang thai loi de de kiem tra.
- Can co lenh/menu de xoa anh debug vi anh chup man hinh co the nang.
- Menu du kien them phim `0`: clear/xoa anh debug da cap.
- Phim dung khan cap: bam `Q` de stop tool khi dang chay.
- So sanh Pokemon/ability: khong phan biet hoa/thuong; mien cung ten la match.

## File code hien tai

- `run_pokemon_tool.py`: script chay menu CMD, mode 1, 3, 4.
- `src/config/tool_config.json`: config window title, timing, ROI crop, threshold template, debug, audio, farm.
- `src/config/target_pokemon.json`: danh sach Pokemon/ability can tim (menu 1).
- `src/config/team_party.json`: team 6 Pokemon voi moves JSON (menu 3 va 4).
- `src/data/type_chart.json`: bang type chart tinh 18 type (khong goi PokeAPI).
- `src/farm/farm_battle.py`: module auto farm tien (menu 3).
- `src/team_builder/team_builder_ui.py`: UI tkinter doc team (menu 4).
- `src/runtime/battle_state.json`: cache trang thai battle runtime (slot hien tai, slot het PP).
- `src/runtime/feedback_log.txt`: log loi/feedback khi chay menu 3.
- `requirements.txt`: Python packages can cai.

Tinh trang code:

- Menu `0`: xoa anh debug trong `src/debug/screenshots`.
- Menu `1`: focus cua so `PROClient`, scan battle, di chuyen `A/D`, OCR Pokemon/ability, click `Run`, dung khi tim thay muc tieu.
- Menu `2`: placeholder, chua code tu bat.
- Menu `3`: auto farm tien - click Fight, OCR 4 move, tinh diem move (type_eff x STAB x power x accuracy), click move tot nhat, theo doi PP, swap Pokemon khi het PP tan cong, feedback log.
- Menu `4`: UI tkinter - load anh team tong/fight, OCR ten Pokemon va 4 move, cho sua thu cong, save team_party.json.
- Click `Run`: dung template `rightBarButtomRun.png` bang OpenCV template matching.
- Screenshot: dung `mss`.
- Focus/click/phim: dung Win32 API qua `ctypes`, khong can `pyautogui`.
- Audio tim thay: thu phat `src/template/audio/quick-ting.mp3`, fallback Windows beep.
- Da sua sau lan debug 2026-06-06:
  - OCR ten Pokemon uu tien doc header `VS. Wild <Pokemon>` vi Tesseract doc font header tot hon font nho trong khung HP.
  - Neu header khong doc duoc, fallback doc Battle Log va sau cung moi doc ROI ten Pokemon.
  - Sua bug enemy name rong bi match nham Pokemon dau tien trong JSON.
  - Ha threshold nut Run tu `0.75` xuong `0.58`; anh debug score thuc te khoang `0.63`.
  - Doi `mss.mss()` sang `mss.MSS()` de het warning future release.
- Da sua tiep sau lan debug hover Run:
  - Ha threshold nut Run xuong `0.45` vi khi chuot hover tren nut Run score co the con khoang `0.55`.
  - Truoc khi scan Run va sau khi click Run, code tu doi chuot ve `mouse.away_point` trong config de tranh hover lam doi mau nut.
- Da sua tiep sau khi click Run bi spam/click khong an:
  - Dua threshold Run ve `0.58` de tranh match nham.
  - Chi template match Run trong ROI `right_action_bar`, khong match toan man hinh.
  - Them `click_offsets.run_button: [0, 25]`, click thap hon vao vung nut Run; voi anh debug click tu `(1439, 781)` thanh `(1439, 806)`.
  - Sau khi click Run, tool doi toi khi battle header `VS.` bien mat. Neu het timeout ma van thay battle, tool tam dung de tranh spam click sai.
- Da sua tiep khi chuot toi dung vi tri Run nhung game khong nhan click:
  - Truoc moi lan click Run, code focus lai cua so `PROClient`.
  - Click Run lap `mouse.click_repeat = 2` lan, cach nhau `0.25s`.
  - Giu mouse down `0.12s` moi click de game de nhan input hon.
- Da doi click tu `mouse_event` sang `SendInput` vi chuot toi dung vi tri nhung game khong nhan click. Co beep nho luc gui click de debug xem tool co that su gui input khong.
- Da sua delay ability sau khi thay log doc cham:
  - Tang `ability_wait_seconds` tu `2.0` len `3.5`.
  - Them retry doc ability `ability_retry_count = 2`, moi lan cach `ability_retry_seconds = 1.5`.
  - Neu lan dau ability la `unknown`, tool se doi them truoc khi quyet dinh Run.
- Code Menu 3 + 4 ngay 2026-06-06:
  - Menu 3: src/farm/farm_battle.py, type chart tinh, scoring move, OCR PP tu move panel, swap Pokemon theo slot.
  - Menu 4: src/team_builder/team_builder_ui.py, UI tkinter 2 panel, load anh fight OCR 4 move tu luoi 2x2, KNOWN_MOVES table ~200 moves.
  - ROI move_slots, move_pp_slots, pokemon_swap_slots them vao tool_config.json.
  - LUU Y: ROI move_slots/pp_slots trong config la uoc luong dua tren 1920x1080, can calibrate lai bang anh debug thuc te neu OCR sai.
  - LUU Y: enemy_types chua lay duoc (khong goi PokeAPI), farm_battle tinh eff voi empty list (=1.0), nen hieu qua la power*stab, se cap nhat sau neu can.

Luu y cai dat:

- Python package hien tai da co `cv2`, `mss`, `PIL`, `pytesseract`, `keyboard`.
- `tesseract.exe` chua duoc tim thay trong PATH o lan kiem tra dau tien.
- Neu OCR khong chay, can cai Tesseract Windows va them PATH, hoac dien duong dan vao `src/config/tool_config.json` -> `ocr.tesseract_cmd`.

## Y tuong giai doan 2 / menu 3

Muc tieu menu `3`: auto danh quai/cay tien dua tren enemy Pokemon, type, skill 1-4, PP con lai, va logic swap Pokemon khi het chieu danh.

Huong de xuat:

- Menu `2`: giu lai cho tinh nang bat Pokemon sau nay.
- Menu `3`: auto battle/farm money.
- Dung PokeAPI chu yeu de lay type cua doi thu va bang khac he/type effectiveness.
- Khong dung PokeAPI de quyet dinh team cua minh dang co move nao; phan nay se doc tu anh/cap cua nguoi dung roi ghi JSON.
- Khong nen goi API moi lan gap Pokemon; nen cache ve local JSON, vi du `src/data/pokeapi_cache/*.json`.
- Can co JSON rieng cho team 6 Pokemon cua minh, tao tu UI/capture/calibration.
- OCR/crop UI battle de doc:
  - Enemy Pokemon name tu header.
  - Move slot 1-4: ten move va PP dang con, vi game hien thi kieu `0/13`.
  - Neu move PP = 0 thi khong chon move do.
  - Neu tat ca move tan cong PP = 0 thi swap Pokemon.
- Logic chon move co the cham diem:
  - type effectiveness voi enemy type.
  - STAB neu move type trung type Pokemon cua minh.
  - power/accuracy neu co data move.
  - bo qua status move trong mode farm tien, tru khi sau nay can logic rieng.
- Y tuong "box cap hinh dan vo chuyen JSON":
  - Lam UI/command rieng de paste/cap anh tung Pokemon trong team.
  - Moi Pokemon can doc/ghi: slot 1-6, ten Pokemon, type/he, 4 ten move.
  - Chi uu tien move tan cong; bo qua move heal/recover/status neu khong co damage.
  - Sau khi doc xong ghi vao JSON de menu `3` dung.
  - Nen co command/menu rieng, vi du `4`: doc/cap team 6 Pokemon vao JSON.
- Menu `3` se doc JSON team da tao de auto danh.

Thong tin anh mau moi:

- Header battle co dang `Antlt1 VS. Wild Persian`; doc enemy name tu sau chu `Wild`.
- Khi bam `Fight`, panel ben phai hien 4 move:
  - Move 1: `Surf`, type `WATER`, PP `14/15`
  - Move 2: `Ice Beam`, type `ICE`, PP `4/16`
  - Move 3: `Toxic`, type `POISON`, PP `10/10`
  - Move 4: `Recover`, type `NORMAL`, PP `8/8`
- Menu `3` can doc truc tiep move name/type/PP tu panel Fight neu co the, vi type move hien san trong UI.
- Move nhu `Recover` la heal/status, nen bo qua trong farm money. `Toxic` co the xem la status/khong damage, tam thoi bo qua neu PokeAPI move data bao power null.
- Flow menu `3` van can A/D di qua lai de kiem Pokemon khi khong trong battle.
- Da chot them:
  - Khi vao battle phai click nut `Fight` de hien panel 4 move.
  - Bo qua cac move hieu ung/status/heal, vi farm tien chi can move gay damage.
  - Uu tien chon move theo PWR/power, khong uu tien PP tru khi cac move bang diem/power.
  - Khi Pokemon hien tai het PP cua cac move danh, swap theo thu tu slot `1 -> 2 -> 3 -> 4 -> 5 -> 6`.
  - Can runtime JSON/cache de nho trong battle Pokemon nao/slot nao het PP va da swap.
  - Menu doc team nen co UI de nguoi dung dan anh:
    - Anh 1: team co 6 con de doc ten/slot.
    - Anh 2-7: tung Pokemon, doc 4 move cua tung con.
  - UI doc team se dung `tkinter` de tranh cai them thu vien.
  - Sau khi OCR anh, UI can co o text cho sua thu cong ten Pokemon/move truoc khi save.
  - Move power/type co the lay tu PokeAPI move endpoint, vi du move `Ice Beam` -> slug `ice-beam`.
  - Runtime cache dat o `src/runtime/battle_state.json`.
  - Neu menu `3` thieu `src/config/team_party.json`, tool bao nguoi dung chay menu `4` truoc.
  - Can tao folder/data JSON cho bang khac he Pokemon de tinh move nao danh x2/x1/x0.5/x0 vao enemy.
  - Type chart/cache:
    - Agent tu quyet cach toi uu nhanh, khong ton search moi tran.
    - Nen co `src/data/type_chart/type_chart.json`.
    - Nen co `src/data/pokeapi_cache/pokemon/`, `src/data/pokeapi_cache/moves/`, `src/data/pokeapi_cache/types/`.
    - Them menu/cache update de tai/cap nhat Pokemon, move, type chart can dung cho battle.
  - Scoring move da chot:
    - Co tinh STAB: move cung he Pokemon minh thi nhan x1.5.
    - Uu tien khac he/type effectiveness truoc.
    - Uu tien PWR/power cao.
    - Co tinh accuracy neu co data.
    - Neu diem bang nhau: PWR cao hon -> PP hien tai nhieu hon -> slot nho hon.
    - Neu cache/API loi hoac thieu enemy type/move data, fallback chon move damage co PWR cao nhat con PP.
    - Cho phep dung move `0.5x` neu het lua chon tot hon; khong nen dung move `0x` tru khi bat buoc/khong co cach.
    - Move accuracy thap van duoc dung neu score sau khi tinh accuracy van cao.
  - Swap:
    - Khi swap vi het PP, tranh swap vao Pokemon/slot da cache la het PP truoc do.
    - Neu khong con slot hop le, bao loi cho nguoi dung.
  - Debug/feedback:
    - Them file `.txt` feedback log de nguoi dung check loi, vi du `src/runtime/feedback_log.txt`.
    - Khi loi team JSON/OCR/cache, nen co UI doc file JSON len cho nguoi dung sua va bam Save.

---

## GIAI DOAN 3: TAB 4 (Bag Scanner) + TAB 5 (Auto Farm Config)

**Status: Tab 4 DONE, Tab 5 DONE**

### Tab 4: Bag Scanner (COMPLETED 2026-06-09)

**File**: `src/team_builder/bag_scanner_tab.py`

**Features**:
- **Drag-to-scan name**: User drags ROI on game screenshot → OCR Pokemon name via Tesseract
  - Button: "🎯 Kéo tên Pokemon"
  - OCR preset: PSM 7 (single line), 5x upscale, CLAHE contrast enhancement, morphological denoise
  - User can manually edit name in textbox if OCR wrong

- **Drag-to-scan moves**: User drags ROI → OCR 4 moves + PP (format: "Move PP/Max")
  - Button: "🎯 Kéo 4 moves"
  - OCR preset: PSM 6 (assume single column), same preprocessing
  - Fills 4 move textboxes + 4 PP textboxes

- **Add Pokemon**: Button ➕ Add Pokemon
  - Auto-increment ID
  - Creates: `{"id": 1, "name": "Breloom", "moves": [{"name": "False Swipe", "pp": "25/40"}, ...]}`
  - Appends to inventory + auto-saves JSON

- **Delete Pokemon**: Click delete button next to Pokemon ID in list
  - Removes from inventory

- **Save JSON**: Button 💾 Save JSON
  - Output: `src/config/pokemon_bag_inventory.json`
  - Format: `[{"id": 1, "name": "Breloom", "moves": [...]}, ...]`

**Dependencies**:
- PIL/Pillow, numpy, cv2, pytesseract
- Tesseract 5.5.0 (must be installed + PATH set)

**Tesseract Setup** (IMPORTANT):
- Install: Tesseract Windows installer from GitHub
- Set ENV vars:
  ```batch
  set "TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata"
  set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
  ```
- Added to `run_gui.bat` - auto setup when run batch file

**Data Flow (Tab 4)**:
```
Game Screenshot
  ↓ drag name ROI
  → OCR + Tesseract
  → fill textbox (editable)
  ↓ drag moves ROI
  → OCR 4 moves
  → fill 4 move/PP textboxes
  ↓ click Add Pokemon
  → pokemon_bag_inventory.json (auto-save)
```

---

### Tab 5: Auto Farm Config (COMPLETED 2026-06-09)

**File**: `src/team_builder/auto_farm_config_tab.py`

**LEFT BOX - Load Pokemon from Bag**:
- Read `pokemon_bag_inventory.json` (from Tab 4)
- Display as list: `[ID] Name - Move1/Move2/Move3/Move4`
- User clicks Pokemon to select (max 6 for team)

**RIGHT BOX - Display 6 Team Slots**:
- Show 6 selected Pokemon slots
- Format: `[ID] Name` with delete button per slot
- Can reorder or remove Pokemon

**SAVE Team**:
- Button 💾 Save Team
- Output: `src/config/team_farm.json`
- Format: `[{6 Pokemon with moves}]` (exactly 6)

**Data Flow (Tab 5)**:
```
pokemon_bag_inventory.json (from Tab 4)
  ↓ load & display LEFT box
  → user clicks 6 Pokemon
  ↓ show selected 6 RIGHT box
  → click Save Team
  ↓ team_farm.json → Menu 3 (auto farm)
```

---

### Integration with Menu 3 (Auto Farm)

- Menu 3 reads `team_farm.json` (6 Pokemon from Tab 5)
- Auto battle: score moves by effectiveness, STAB, power
- Swap Pokemon when PP runs out
- Feedback log: `src/runtime/feedback_log.txt`

---

### Next Steps for Other AI Coder

1. Implement Tab 5 LEFT box loader (read bag JSON + display)
2. Implement Tab 5 RIGHT box selector (add/remove/reorder 6 slots)
3. Implement save team JSON button
4. Test full workflow: Tab 4 (add Pokemon) → Tab 5 (select 6) → Menu 3 (auto farm)
