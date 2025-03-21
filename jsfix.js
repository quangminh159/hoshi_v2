// Phần cần sửa 1 - Hàm submitComment
function submitComment(postId) {
    const form = document.querySelector(`#post-${postId} .comment-form`);
    const commentInput = form.querySelector('.comment-input');
    const replyInfo = form.querySelector('.reply-info');
    const parentId = form.getAttribute('data-parent-id');
    const text = commentInput.value.trim();
    
    if (text) {
        fetch('/api/posts/comments/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                post_id: postId,
                text: text,
                parent_id: parentId
            })
        })
        .then(response => response.json())
        .then(data => {
            // ... phần còn lại không thay đổi
        })
    }
}

// Phần cần sửa 2 - Xử lý form bình luận
// Trong phần xử lý submit form bình luận (khoảng dòng 519)
if (text) {
    // Gửi bình luận lên server
    fetch('/api/posts/comments/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            post_id: postId,
            text: text,
            parent_id: parentId
        })
    })
    .then(response => response.json())
    .then(data => {
        // ... phần còn lại không thay đổi
    })
}

function likePost(postId) {
    fetch(`/posts/${postId}/like/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // Kiểm tra trạng thái phản hồi
        if (!response.ok) {
            // Nếu phản hồi không thành công, ném ra lỗi
            return response.json().then(errorData => {
                throw new Error(errorData.message || 'Không thể thực hiện thao tác like');
            });
        }
        return response.json();
    })
    .then(data => {
        // Tìm tất cả các nút like cho bài post này
        const likeButtons = document.querySelectorAll(`.like-button[data-post-id="${postId}"]`);
        const likeCountElements = document.querySelectorAll(`.likes-count[data-post-id="${postId}"]`);
        
        likeButtons.forEach(likeButton => {
            const heartIcon = likeButton.querySelector('i');
            if (data.status === 'liked') {
                // Thêm hiệu ứng like 
                heartIcon.classList.remove('far');
                heartIcon.classList.add('fas', 'text-danger');
                
                // Hiển thị thông báo like thành công
                showNotification('Đã thích bài viết', 'success');
            } else if (data.status === 'unliked') {
                heartIcon.classList.remove('fas', 'text-danger');
                heartIcon.classList.add('far');
                
                // Hiển thị thông báo bỏ like
                showNotification('Đã bỏ thích bài viết', 'info');
            }
        });

        // Cập nhật số lượng like
        likeCountElements.forEach(likeCount => {
            likeCount.textContent = data.likes_count;
        });
    })
    .catch(error => {
        // Xử lý các lỗi chi tiết
        console.error('Lỗi khi like bài viết:', error);
        
        // Hiển thị thông báo lỗi cụ thể
        if (error.message.includes('authentication')) {
            showNotification('Vui lòng đăng nhập để thực hiện thao tác', 'warning');
        } else if (error.message.includes('permission')) {
            showNotification('Bạn không có quyền thực hiện thao tác này', 'error');
        } else {
            showNotification('Có lỗi xảy ra. Vui lòng thử lại sau', 'error');
        }
    });
}

// Hàm hiển thị thông báo
function showNotification(message, type = 'info') {
    // Tạo container thông báo nếu chưa tồn tại
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '1050';
        document.body.appendChild(notificationContainer);
    }

    // Tạo phần tử thông báo
    const notification = document.createElement('div');
    notification.className = `alert alert-${getBootstrapClass(type)} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Thêm thông báo vào container
    notificationContainer.appendChild(notification);

    // Tự động ẩn thông báo sau 3 giây
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, 3000);
}

// Hàm chuyển đổi loại thông báo sang class Bootstrap
function getBootstrapClass(type) {
    switch(type) {
        case 'success': return 'success';
        case 'error': return 'danger';
        case 'warning': return 'warning';
        default: return 'info';
    }
} 