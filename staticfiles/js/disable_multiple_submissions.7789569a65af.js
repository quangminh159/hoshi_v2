/**
 * Script ngăn người dùng gửi form nhiều lần
 * Thêm vào layout/template chính của ứng dụng
 */

// Đợi cho trang tải xong
document.addEventListener('DOMContentLoaded', function() {
    // Áp dụng cho tất cả form trên trang
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            // Kiểm tra nếu form đã đang được gửi
            if (this.classList.contains('submitting')) {
                console.log('Đã chặn gửi form trùng lặp');
                e.preventDefault();
                return false;
            }
            
            // Đánh dấu form đang gửi
            this.classList.add('submitting');
            
            // Vô hiệu hóa nút gửi
            const submitButtons = this.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(button => {
                const originalText = button.textContent || button.value;
                if (button.tagName === 'BUTTON') {
                    button.setAttribute('data-original-text', originalText);
                    button.textContent = 'Đang gửi...';
                } else {
                    button.setAttribute('data-original-value', button.value);
                    button.value = 'Đang gửi...';
                }
                button.disabled = true;
            });
            
            // Đặt timeout để reset form sau 5 giây (phòng hờ trường hợp request lỗi)
            setTimeout(() => {
                resetForm(this);
            }, 5000);
        });
    });

    // Bắt sự kiện click nút gửi bình luận
    document.querySelectorAll('.comment-form button, .post-form button').forEach(button => {
        button.addEventListener('click', function(e) {
            const form = this.closest('form');
            if (!form) return;
            
            if (this.classList.contains('clicked')) {
                console.log('Đã chặn gửi nhiều lần');
                e.preventDefault();
                return false;
            }
            
            this.classList.add('clicked');
            const originalText = this.textContent;
            this.setAttribute('data-original-text', originalText);
            this.textContent = 'Đang gửi...';
            this.disabled = true;
            
            setTimeout(() => {
                this.classList.remove('clicked');
                this.textContent = originalText;
                this.disabled = false;
            }, 3000);
        });
    });
});

// Hàm reset form về trạng thái ban đầu
function resetForm(form) {
    form.classList.remove('submitting');
    
    const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    submitButtons.forEach(button => {
        if (button.tagName === 'BUTTON') {
            const originalText = button.getAttribute('data-original-text');
            if (originalText) {
                button.textContent = originalText;
            }
        } else {
            const originalValue = button.getAttribute('data-original-value');
            if (originalValue) {
                button.value = originalValue;
            }
        }
        button.disabled = false;
    });
}

// Thêm CSS cho trạng thái submitting
const style = document.createElement('style');
style.textContent = `
    form.submitting {
        opacity: 0.8;
        pointer-events: none;
    }
    button.clicked {
        opacity: 0.7;
        cursor: not-allowed;
    }
`;
document.head.appendChild(style); 