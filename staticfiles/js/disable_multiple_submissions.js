/**
 * Script để ngăn gửi form nhiều lần
 */
document.addEventListener('DOMContentLoaded', function() {
    // Đảm bảo script không chạy nhiều lần
    if (window.formSubmissionHandled) return;
    window.formSubmissionHandled = true;
    
    console.log('Đã tải script prevent multiple submissions');
    
    // Xử lý tất cả các form trên trang
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('Form đang được gửi:', form);
            
            // Nếu form đã được đánh dấu là đang gửi, ngăn gửi lại
            if (this.classList.contains('submitting')) {
                console.log('Đã chặn gửi form trùng lặp');
                e.preventDefault();
                return false;
            }
            
            // Đánh dấu form đang được gửi
            this.classList.add('submitting');
            console.log('Đã đánh dấu form là đang gửi');
            
            // Tìm nút submit và vô hiệu hóa
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.textContent;
                submitButton.setAttribute('data-original-text', originalText);
                submitButton.textContent = 'Đang gửi...';
                submitButton.disabled = true;
                console.log('Đã vô hiệu hóa nút submit');
            }
        });
    });
});
