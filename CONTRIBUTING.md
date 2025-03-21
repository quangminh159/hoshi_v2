# Hướng dẫn đóng góp

Cảm ơn bạn đã quan tâm đến việc đóng góp cho Hoshi! Chúng tôi rất hoan nghênh mọi đóng góp từ cộng đồng.

## Quy trình đóng góp

1. Fork repository này về tài khoản GitHub của bạn
2. Tạo một nhánh mới cho tính năng hoặc sửa lỗi của bạn:
   ```bash
   git checkout -b feature/ten-tinh-nang
   ```
   hoặc
   ```bash
   git checkout -b fix/ten-loi
   ```

3. Thực hiện các thay đổi của bạn và commit:
   ```bash
   git add .
   git commit -m "Mô tả ngắn gọn về thay đổi"
   ```

4. Push lên fork của bạn:
   ```bash
   git push origin feature/ten-tinh-nang
   ```

5. Tạo Pull Request từ nhánh của bạn vào nhánh `main` của repository gốc

## Quy tắc đóng góp

### Commit

- Sử dụng tiếng Việt hoặc tiếng Anh trong commit message
- Commit message nên ngắn gọn và mô tả rõ thay đổi
- Mỗi commit nên tập trung vào một thay đổi cụ thể

### Code style

- Tuân thủ PEP 8 cho Python code
- Sử dụng 4 spaces cho indentation
- Giới hạn độ dài mỗi dòng là 79 ký tự
- Thêm docstring cho các class và function mới
- Đặt tên biến và function bằng tiếng Anh, rõ ràng và có ý nghĩa

### Pull Requests

- Mô tả chi tiết các thay đổi trong PR
- Thêm test cases cho các tính năng mới
- Đảm bảo tất cả tests đều pass
- Cập nhật documentation nếu cần thiết
- Giải quyết các conflicts trước khi yêu cầu review

### Issues

- Kiểm tra xem issue đã tồn tại chưa trước khi tạo mới
- Sử dụng template có sẵn khi tạo issue
- Cung cấp thông tin chi tiết và rõ ràng về vấn đề
- Thêm labels phù hợp cho issue

## Quy trình review

1. Maintainers sẽ review PR của bạn
2. Có thể yêu cầu một số thay đổi hoặc làm rõ
3. Sau khi được chấp nhận, PR sẽ được merge vào nhánh chính

## Báo cáo lỗi bảo mật

Nếu bạn phát hiện lỗi bảo mật, vui lòng không tạo public issue. Thay vào đó, hãy gửi email đến quangminh159159@gmail.com.

## Liên hệ

Nếu bạn có bất kỳ câu hỏi nào, vui lòng:
- Tạo issue trên GitHub
- Gửi email đến quangminh159159@gmail.com
- Tham gia kênh Discord của chúng tôi

## License

Bằng cách đóng góp cho Hoshi, bạn đồng ý rằng các đóng góp của bạn sẽ được cấp phép theo giấy phép MIT. 