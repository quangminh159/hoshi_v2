# CÂU HỎI VÀ ĐÁP ÁN BẢO VỆ ĐỒ ÁN HOSHI

## PHẦN 1: KIẾN TRÚC VÀ THIẾT KẾ HỆ THỐNG

### Câu 1: Tại sao bạn chọn Django làm framework cho dự án này?
**Đáp án:**
- Django là framework full-stack với nhiều tính năng có sẵn phù hợp với mạng xã hội
- Hệ thống admin mạnh mẽ giúp quản lý dữ liệu dễ dàng
- ORM tích hợp giúp thao tác với cơ sở dữ liệu không phụ thuộc loại database
- Hệ thống xác thực (authentication) được tích hợp sẵn, dễ mở rộng
- Django Channels hỗ trợ WebSocket cho tính năng chat và thông báo thời gian thực
- Cộng đồng lớn, nhiều thư viện hỗ trợ và tài liệu phong phú

### Câu 2: Hệ thống kiến trúc của dự án được thiết kế như thế nào?
**Đáp án:**
- Kiến trúc MTV (Model-Template-View) của Django:
  - Models: Định nghĩa cấu trúc dữ liệu (User, Profile, Post, Comment, Chat...)
  - Templates: Giao diện người dùng (HTML, CSS, JS)
  - Views: Xử lý logic nghiệp vụ
- Kiến trúc microservices nhỏ trong một monolith:
  - Accounts: Quản lý người dùng, xác thực
  - Posts: Đăng bài, tương tác, feed
  - Chat: Nhắn tin trực tiếp
  - Notifications: Hệ thống thông báo
- API RESTful cho ứng dụng di động và tương tác frontend
- WebSocket cho giao tiếp thời gian thực

### Câu 3: Bạn đã triển khai WebSocket cho chức năng chat như thế nào?
**Đáp án:**
- Sử dụng Django Channels làm nền tảng WebSocket
- ASGI thay vì WSGI để hỗ trợ giao tiếp bất đồng bộ
- Thiết kế consumer classes xử lý kết nối và tin nhắn
- Xác thực WebSocket qua token hoặc session
- Cấu trúc dữ liệu tin nhắn phân loại theo room/conversation
- Lưu trữ tin nhắn trong database và truyền tải real-time
- Redis làm channel layer cho việc mở rộng theo chiều ngang

### Câu 4: Chiến lược lưu trữ và quản lý media trong hệ thống?
**Đáp án:**
- Sử dụng Django-imagekit để xử lý ảnh:
  - Tạo nhiều phiên bản ảnh khác nhau (thumbnail, medium, large)
  - Tối ưu hóa ảnh tự động (nén, thay đổi kích thước)
- Lưu trữ file phân cấp theo ngày/tháng/người dùng
- Sử dụng whitenoise cho static files trong development
- Chiến lược cho production:
  - Lưu trữ media trên cloud storage (AWS S3 hoặc tương tự)
  - CDN để phân phối nội dung nhanh chóng
- Xử lý video với kích thước giới hạn và transcode tự động

## PHẦN 2: BẢO MẬT

### Câu 1: Dự án triển khai các biện pháp bảo mật nào?
**Đáp án:**
- Xác thực đa yếu tố (2FA) với django-otp
- Mã hóa mật khẩu với thuật toán bcrypt/PBKDF2
- CSRF protection trên các form và API
- Bảo vệ chống XSS qua Django template system
- Content Security Policy
- Middleware kiểm tra trạng thái tài khoản (AccountStatusMiddleware)
- Kiểm soát truy cập dựa trên permission
- Giới hạn rate-limit cho API
- Xác thực OAuth bảo mật với các nhà cung cấp (Google, Facebook, Apple)

### Câu 2: Hệ thống xác thực hai lớp (2FA) được triển khai như thế nào?
**Đáp án:**
- Sử dụng django-otp và django-two-factor-auth
- Hỗ trợ nhiều phương thức xác thực:
  - TOTP (Time-based One-Time Password) qua ứng dụng như Google Authenticator
  - SMS (tin nhắn văn bản)
  - Backup codes cho trường hợp khẩn cấp
- Quy trình đăng ký 2FA:
  - Tạo secret key và hiển thị QR code
  - Xác nhận bằng mã OTP đầu tiên
  - Cung cấp backup codes
- Tích hợp với luồng đăng nhập thông thường
- Tùy chọn bắt buộc 2FA cho tài khoản quản trị

### Câu 3: Cách xử lý dữ liệu nhạy cảm như mật khẩu và thông tin cá nhân?
**Đáp án:**
- Mật khẩu được hash sử dụng PBKDF2 với nhiều vòng lặp
- Không lưu trữ thông tin thanh toán nhạy cảm
- Mã hóa một chiều cho dữ liệu cực kỳ nhạy cảm
- Tuân thủ nguyên tắc least privilege khi truy cập dữ liệu
- Xóa token và session hết hạn
- Phân quyền chi tiết cho từng loại dữ liệu
- Kiểm soát truy cập vào API dựa trên quyền người dùng
- Audit logging cho các thao tác quan trọng

## PHẦN 3: CHỨC NĂNG VÀ TÍNH NĂNG

### Câu 1: Thuật toán feed của bạn hoạt động như thế nào?
**Đáp án:**
- Kết hợp nhiều yếu tố để xếp hạng bài viết:
  - Thời gian đăng (mới hơn được ưu tiên)
  - Mức độ tương tác (lượt thích, bình luận)
  - Mối quan hệ với người đăng (follow, tương tác trước đó)
  - Tính phổ biến của hashtag
- Triển khai trong module feed_algorithms.py
- Pagination và lazy loading để tối ưu hiệu suất
- Cache kết quả feed cho truy cập nhanh
- Hỗ trợ chế độ xem theo thời gian (chronological)
- Khả năng cá nhân hóa dựa trên lịch sử tương tác

### Câu 2: Cơ chế upload và xử lý ảnh/video trong hệ thống?
**Đáp án:**
- Frontend:
  - JavaScript cho phép chọn nhiều file
  - Xem trước và crop ảnh trước khi upload
  - Upload không đồng bộ với progress bar
- Backend:
  - Kiểm tra kích thước và loại file
  - Xử lý metadata (EXIF) và loại bỏ dữ liệu nhạy cảm
  - Tạo nhiều phiên bản ảnh với django-imagekit
  - Xử lý video với ffmpeg (nếu cần)
- Lưu trữ:
  - Phân cấp thư mục theo user/date
  - Đổi tên file để tránh xung đột
  - Áp dụng nén cho tối ưu dung lượng
  - CDN cho phân phối nội dung

### Câu 3: Hệ thống thông báo thời gian thực được thiết kế như thế nào?
**Đáp án:**
- Kiến trúc publisher-subscriber với Django Channels
- Signals Django để tạo thông báo khi có sự kiện (comment, like, follow)
- Lưu trữ thông báo trong database với trạng thái đã đọc/chưa đọc
- WebSocket để gửi thông báo tới người dùng trong thời gian thực
- Batch processing cho thông báo hàng loạt
- Prioritization cho thông báo quan trọng
- Badge counter và notification center trong UI
- Email/push notification cho người dùng không online

## PHẦN 4: HIỆU SUẤT VÀ TỐI ƯU HÓA

### Câu 1: Các chiến lược tối ưu hóa nào đã được áp dụng?
**Đáp án:**
- Database:
  - Indexing cho các trường tìm kiếm thường xuyên
  - Select_related và prefetch_related để giảm số lượng query
  - Database connection pooling
- Caching:
  - Cache template fragments
  - Cache kết quả query phức tạp
  - Cache user sessions
- Static/Media:
  - Nén và minify CSS/JS
  - Lazy loading images
  - Sử dụng CDN cho static files
- Optimization:
  - Pagination cho danh sách dài
  - Lazy loading cho infinite scroll
  - Dùng task bất đồng bộ với Celery cho xử lý nặng

### Câu 2: Làm thế nào để xử lý tải cao khi có nhiều người dùng?
**Đáp án:**
- Horizontal scaling với nhiều server application
- Load balancing để phân phối traffic
- Database sharding nếu cần thiết
- Redis làm message broker và cache
- Celery workers để xử lý tác vụ nặng
- WebSocket clustering với Django Channels và Redis
- Rate limiting cho API endpoints
- Tối ưu hóa điểm nghẽn (bottlenecks) đã xác định
- Monitoring để phát hiện sớm vấn đề hiệu suất

## PHẦN 5: TRIỂN KHAI VÀ VẬN HÀNH

### Câu 1: Chiến lược triển khai của dự án là gì?
**Đáp án:**
- CI/CD pipeline:
  - GitHub Actions cho automated testing
  - Auto-deploy khi merge vào nhánh chính
- Triển khai trên Railway:
  - PaaS giúp đơn giản hóa deployment
  - Auto-scaling dựa trên nhu cầu
  - Zero-downtime deployments
- Môi trường:
  - Development (local)
  - Staging (preview)
  - Production
- Containerization với Docker:
  - Đóng gói ứng dụng và dependencies
  - Consistency giữa các môi trường
  - Docker Compose cho local development
- Database migration an toàn
- Backup strategy và disaster recovery plan

### Câu 2: Giải thích cách sử dụng Ngrok trong phát triển?
**Đáp án:**
- Mục đích sử dụng Ngrok:
  - Tạo public URL cho localhost
  - Kiểm thử OAuth callback
  - Kiểm thử trên thiết bị di động
  - Demo ứng dụng từ xa
- Quy trình tự động:
  - Script start_server_with_ngrok.bat khởi động server và Ngrok
  - auto_update_ngrok.py cập nhật cấu hình CSRF và OAuth URLs
- Thách thức:
  - URL thay đổi mỗi lần khởi động (phiên bản miễn phí)
  - Cần cập nhật callback URLs trong cấu hình OAuth
  - Giới hạn 2 giờ cho mỗi session
  - Bandwidth giới hạn
- Giải pháp:
  - Tự động hóa quy trình cập nhật
  - Sử dụng custom domain nếu cần ổn định

## PHẦN 6: KINH NGHIỆM VÀ THÁCH THỨC

### Câu 1: Những thách thức lớn nhất trong quá trình phát triển?
**Đáp án:**
- Kỹ thuật:
  - Triển khai WebSocket cho chat và notifications
  - Tối ưu hóa hiệu suất với lượng dữ liệu lớn
  - Xử lý oauth và social authentication
  - Tuỳ chỉnh django-allauth
- Thiết kế:
  - Tạo UX/UI thân thiện và phản hồi nhanh
  - Xây dựng feed algorithm cân bằng
  - Thiết kế database schema linh hoạt
- Vận hành:
  - Cấu hình môi trường development giống production
  - Khắc phục vấn đề với social auth callbacks
  - Triển khai và scale hệ thống

### Câu 2: Kế hoạch phát triển trong tương lai?
**Đáp án:**
- Tính năng mới:
  - Story và Reels nâng cao
  - Direct Message với end-to-end encryption
  - Live streaming
  - Marketplace/E-commerce integration
- Cải tiến kỹ thuật:
  - Chuyển sang microservices architecture
  - Progressive Web App (PWA)
  - GraphQL API thay thế REST
  - Machine Learning cho feed và đề xuất
- Mở rộng:
  - Phát triển ứng dụng di động native
  - Internationalization và localization
  - Analytics và business intelligence
  - API mở cho third-party developers

## PHẦN 7: QUY TRÌNH PHÁT TRIỂN

### Câu 1: Quy trình phát triển phần mềm áp dụng trong dự án?
**Đáp án:**
- Agile/Scrum methodology:
  - Sprint 2 tuần
  - Daily standup meeting
  - Sprint review và retrospective
- Git workflow:
  - Feature branches
  - Pull requests và code review
  - CI/CD automation
- Testing strategy:
  - Unit tests cho logic nghiệp vụ
  - Integration tests cho API endpoints
  - End-to-end tests cho luồng người dùng chính
- Documentation:
  - API documentation với Swagger/OpenAPI
  - Development guide và README
  - User documentation

### Câu 2: Cách thực hiện kiểm thử trong dự án?
**Đáp án:**
- Unit testing với pytest:
  - Test models, views, và business logic
  - Mocking external services
- Integration testing:
  - API testing với DRF test framework
  - Database interaction tests
- End-to-end testing:
  - Selenium cho browser automation
  - User flow testing
- Test coverage tracking
- Automated testing trong CI pipeline
- Manual testing cho UX và visual bugs
- Security testing với các công cụ tự động
- Performance testing cho database queries và page load 