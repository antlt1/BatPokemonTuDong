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

## File code ban dau

- `run_pokemon_tool.py`: script chay menu CMD va mode 1.
- `src/config/tool_config.json`: config window title, timing, ROI crop, threshold template, debug, audio.
- `src/config/target_pokemon.json`: danh sach Pokemon/ability can tim.
- `requirements.txt`: Python packages can cai.

Tinh trang code:

- Menu `0`: xoa anh debug trong `src/debug/screenshots`.
- Menu `1`: focus cua so `PROClient`, scan battle, di chuyen `A/D`, OCR Pokemon/ability, click `Run`, dung khi tim thay muc tieu.
- Menu `2`: placeholder, chua code tu bat.
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

Luu y cai dat:

- Python package hien tai da co `cv2`, `mss`, `PIL`, `pytesseract`, `keyboard`.
- `tesseract.exe` chua duoc tim thay trong PATH o lan kiem tra dau tien.
- Neu OCR khong chay, can cai Tesseract Windows va them PATH, hoac dien duong dan vao `src/config/tool_config.json` -> `ocr.tesseract_cmd`.
