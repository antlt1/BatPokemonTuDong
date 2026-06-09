# Nâng cấp toàn diện UI cho PokemonPRO Auto Farm

Ý tưởng chuyển đổi toàn bộ Tool từ màn hình CMD đen trắng sang một giao diện đồ họa (GUI) hiện đại là một bước tiến tuyệt vời! Việc này sẽ giúp Tool trông chuyên nghiệp như một phần mềm thực thụ.

![Giao diện minh họa (Mockup)](/C:/Users/antlt/.gemini/antigravity/brain/05314e5b-9e43-427a-b365-70cda57ee1a3/modern_pokemon_bot_ui_1780937402610.png)

## Các công nghệ UI hiện đại cho Python:
1. **CustomTkinter (Đề xuất tối ưu nhất)**: Đây là một thư viện bọc ngoài Tkinter (chuẩn mà Tool đang dùng ở Menu 4). Nó mang lại giao diện Dark Mode, bo góc cực kỳ hiện đại (giống Windows 11 / Discord) mà **không đòi hỏi phải đập đi xây lại toàn bộ code cũ**.
2. **PyQt6 / PySide6**: Cực kỳ mạnh mẽ, chuyên nghiệp nhưng nặng và phải viết lại code UI từ đầu.
3. **Flet (Flutter for Python)**: Giao diện tuyệt đẹp mang hơi hướng Web/Mobile, có hiệu ứng mượt mà nhưng đòi hỏi cấu trúc code khác biệt hoàn toàn.

👉 **Lựa chọn của mình:** Chúng ta nên dùng **CustomTkinter** để giữ lại các Tab Calibrate ROI và Team Builder hiện có, chỉ việc "khoác" cho nó một bộ áo mới sang trọng hơn, đồng thời nhúng luôn cái Bảng điều khiển (Dashboard) thay cho CMD vào đó.

## Kế hoạch triển khai (Proposed Changes)

Để đưa toàn bộ Tool lên giao diện đồ họa, chúng ta cần thay đổi cấu trúc luồng (Threading) vì nếu để Auto Farm chạy chung luồng với UI thì giao diện sẽ bị đơ (Freeze).

### 1. Nâng cấp Thư viện & Cấu trúc chính
- Cài đặt thư viện `customtkinter`.
- Tạo một file `modern_ui.py` đóng vai trò là cửa sổ chính của toàn bộ ứng dụng.

### 2. Thiết kế Cửa sổ chính (Main Window)
Giao diện sẽ được chia làm 2 phần chính:
- **Sidebar (Cột bên trái)**: Chứa các nút chuyển Tab (Dashboard, Team Builder, Calibrate ROI, Settings).
- **Main Content (Phần bên phải)**:
  - **Tab Dashboard**: Chứa các nút Start/Stop to bành, hiển thị chế độ hiện tại (Mode 2, Mode 3), và một khung Log (thay cho màn hình đen CMD) để chữ tự động nhảy lên.
  - **Tab Team Builder**: Chuyển giao diện Team Builder cũ sang giao diện Dark Mode của CustomTkinter.
  - **Tab Calibrate ROI**: Chuyển giao diện chỉnh tọa độ sang CustomTkinter.

### 3. Xử lý Đa luồng (Threading)
- Khi bấm nút `Start Auto Farm`, Tool sẽ tạo ra một luồng (Thread) chạy ngầm (Background Worker) để thực thi file `farm_battle.py`.
- Hàm in log (như `print` hay `feedback_log`) sẽ được kết nối để bắn chữ trực tiếp lên màn hình GUI thay vì in ra CMD.
- Nút `Stop` sẽ gửi tín hiệu dừng luồng an toàn.

## Open Questions
> [!IMPORTANT]
> 1. Bạn đồng ý sử dụng **CustomTkinter** để nâng cấp UI chứ? (Nếu bạn thích phong cách web bóng bẩy hơn, mình có thể dùng Flet, nhưng CustomTkinter là an toàn và ổn định nhất cho app Auto click).
> 2. Bạn muốn cài đặt phím tắt (Hotkey) để bật/tắt Tool khi đang trong game là nút nào? (Ví dụ: F8 để Start/Stop, hay vẫn giữ nguyên bấm Q để Stop?).

Vui lòng xem xét kế hoạch và ảnh Mockup ở trên. Nếu bạn đồng ý, hãy phản hồi để mình tiến hành đập đi xây lại cái giao diện xịn xò này nhé!
