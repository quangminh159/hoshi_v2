# Hướng dẫn chạy Hoshi + ngrok (test điện thoại / 4G)

Cần **2 terminal** mở cùng lúc trong thư mục `C:\hoshi_v2`.

---

## Bước 1 — Chạy server (Daphne)

Mở PowerShell:

```powershell
cd C:\hoshi_v2
.\venv\Scripts\python.exe -m daphne -b 0.0.0.0 -p 8000 hoshi.asgi:application
```

Thấy dòng kiểu `Listening on TCP address 0.0.0.0:8000` là OK.
**Giữ terminal này chạy**, đừng tắt.

> Dùng đúng `.\venv\Scripts\python.exe` (không dùng `python` hệ thống).
> Không dùng `manage.py runserver` nếu cần chat / WebSocket / gọi thoại.

---

## Bước 2 — Mở tunnel ngrok

Mở PowerShell thứ 2:

```powershell
cd C:\hoshi_v2
.\ngrok.exe http 8000
```

Trên màn hình ngrok sẽ hiện URL dạng:

```text
https://xxxx-xx-xx-xx-xx.ngrok-free.app
```

Copy URL đó.

Hoặc trên máy PC mở: http://127.0.0.1:4040 để xem / copy link.

**Giữ terminal ngrok chạy** trong lúc test.

---

## Bước 3 — Mở trên điện thoại

1. Dán URL `https://....ngrok-free.app` vào trình duyệt điện thoại
2. Lần đầu ngrok free hiện trang cảnh báo → bấm **Visit Site**
3. Đăng nhập Hoshi và test như bình thường (kể cả trên 4G)

---

## Tắt / khởi động lại

**Tắt server**

```powershell
netstat -ano | findstr ":8000"
Stop-Process -Id <PID> -Force
```

**Tắt ngrok:** `Ctrl + C` ở terminal ngrok, hoặc đóng cửa sổ đó.

Mỗi lần tắt rồi bật lại ngrok, **URL có thể đổi** → copy URL mới.

---

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Listen failure` / port 8000 bị chiếm | Tìm PID bằng `netstat` rồi `Stop-Process`, chạy lại Daphne |
| Điện thoại không vào được | Kiểm tra cả 2 terminal còn chạy; URL đúng `https://` |
| CSRF / không submit form | Đảm bảo `CSRF_TRUSTED_ORIGINS` có `https://*.ngrok-free.app` (đã có trong settings) |
| Chat / gọi không realtime | Phải dùng Daphne, không dùng `runserver` |
| Gọi video/thoại qua 4G | Cần HTTPS (ngrok) + TURN (project đã có fallback Metered) |

---

## Gọi thoại / video (nhắc nhanh)

- Ưu tiên cửa sổ riêng `/chat/call/`
- Trình duyệt chặn popup → gọi ngay trên trang vẫn được
- Cho phép popup: thanh địa chỉ → icon bị chặn → Luôn cho phép
- Đóng cửa sổ gọi = cúp máy
