// Biến để giám sát quá trình xử lý event
window.Hoshi = window.Hoshi || {};
window.Hoshi.processedEvents = new Set();
window.Hoshi.processedRequests = new Set();
window.Hoshi.debug = true;

// Hàm debounce - chỉ xử lý sau một khoảng thời gian kể từ lần cuối cùng được gọi
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// Hàm throttle - chỉ xử lý một lần trong khoảng thời gian xác định
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Hàm bọc để tránh đăng ký trùng lặp event listeners
function safeAddEventListener(element, eventType, handler, handlerId) {
    if (!element || !eventType || !handler) return;
    
    // Tạo ID duy nhất cho handler
    const uniqueId = handlerId || `${eventType}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Nếu event listener này đã được đăng ký cho element, bỏ qua
    if (window.Hoshi.processedEvents.has(uniqueId)) {
        if (window.Hoshi.debug) console.log(`Bỏ qua event listener đã tồn tại: ${uniqueId}`);
        return;
    }
    
    // Đánh dấu đã xử lý
    window.Hoshi.processedEvents.add(uniqueId);
    
    // Đăng ký event listener
    element.addEventListener(eventType, handler);
    if (window.Hoshi.debug) console.log(`Đã đăng ký event listener: ${uniqueId}`);
}

// Override XMLHttpRequest để debug requests
(function() {
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url) {
        this._requestMethod = method;
        this._requestUrl = url;
        return originalOpen.apply(this, arguments);
    };
    
    XMLHttpRequest.prototype.send = function(data) {
        if (window.Hoshi.debug && this._requestUrl && this._requestUrl.includes('/api/posts/comments/add')) {
            console.log(`XHR ${this._requestMethod} to ${this._requestUrl}`);
            console.log('Request data:', data);
        }
        return originalSend.apply(this, arguments);
    };
})();

// Override fetch API để debug requests
(function() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options) {
        if (window.Hoshi.debug && url && url.includes('/api/posts/comments/add')) {
            console.log(`Fetch to ${url}`, options);
            if (options && options.body) {
                console.log('Request data:', options.body);
            }
        }
        return originalFetch.apply(this, arguments);
    };
})();

// Override jQuery.ajax để debug requests
if (typeof jQuery !== 'undefined') {
    (function($) {
        const originalAjax = $.ajax;
        
        $.ajax = function(options) {
            if (window.Hoshi.debug && options && options.url && options.url.includes('/api/posts/comments/add')) {
                console.log('jQuery AJAX to ' + options.url, options);
            }
            return originalAjax.apply(this, arguments);
        };
    })(jQuery);
}

// Khoá các DOM elements đã được xử lý
document.addEventListener('DOMContentLoaded', function() {
    // Tự động khoá các form comment
    if (window.Hoshi.debug) console.log('DOMContentLoaded - Khoá các form comment');
    
    // Nếu đã có DOMContentLoaded trước đó, vẫn tiếp tục nhưng chỉ chạy một số tác vụ cần thiết
    if (window.Hoshi.domLoaded) {
        if (window.Hoshi.debug) console.log('DOMContentLoaded đã chạy trước đó, chỉ cập nhật các phần tử mới');
        return;
    }
    
    window.Hoshi.domLoaded = true;

    // Initialize Bootstrap tooltips and popovers
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Load initial unread notifications count
    if ($('#unread-notifications').length) {
        loadUnreadNotificationsCount();
        // Refresh count every minute
        setInterval(loadUnreadNotificationsCount, 60000);
    }

    // Handle alert dismissal
    $('.alert').alert();

    // Thêm event listener cho nút like post
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            likePost(postId);
        });
    });
    
    // Xử lý nút like comment
    document.querySelectorAll('.like-comment-button').forEach(button => {
        button.addEventListener('click', function() {
            const commentId = this.getAttribute('data-comment-id');
            if (commentId) {
                likeComment(commentId);
            }
        });
    });

    // Xử lý nút save post
    document.querySelectorAll('.save-button').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            savePost(postId);
        });
    });
});

// Like post
function likePost(postId) {
    fetch(`/api/posts/${postId}/like/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const likeButtons = document.querySelectorAll(`.like-button[data-post-id="${postId}"]`);
        const likeCountElements = document.querySelectorAll(`.likes-count[data-post-id="${postId}"]`);
        const likeCountDisplays = document.querySelectorAll(`.likes-count-display a[data-post-id="${postId}"]`);
        
        likeButtons.forEach(likeButton => {
            const heartIcon = likeButton.querySelector('i');
            if (data.status === 'liked') {
                heartIcon.classList.remove('far');
                heartIcon.classList.add('fas');
            } else if (data.status === 'unliked') {
                heartIcon.classList.remove('fas');
                heartIcon.classList.add('far');
            }
        });

        likeCountElements.forEach(likeCount => {
            likeCount.textContent = data.likes_count;
        });

        likeCountDisplays.forEach(likeCountDisplay => {
            likeCountDisplay.textContent = `${data.likes_count} lượt thích`;
        });
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Có lỗi xảy ra khi thích bài viết');
    });
}

// Follow user
function followUser(userId) {
    fetch(`/api/users/${userId}/follow/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const followButton = document.querySelector(`#user-${userId} .follow-button`);
            
            if (data.following) {
                followButton.textContent = 'Đang theo dõi';
                followButton.classList.remove('btn-primary');
                followButton.classList.add('btn-secondary');
            } else {
                followButton.textContent = 'Theo dõi';
                followButton.classList.remove('btn-secondary');
                followButton.classList.add('btn-primary');
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Save post
function savePost(postId) {
    fetch(`/api/posts/${postId}/save/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const saveButton = document.querySelector(`.save-button[data-post-id="${postId}"]`);
        if (saveButton) {
            const icon = saveButton.querySelector('i');
            
            if (data.status === 'saved') {
                icon.classList.remove('far');
                icon.classList.add('fas');
            } else if (data.status === 'unsaved') {
                icon.classList.remove('fas');
                icon.classList.add('far');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Có lỗi xảy ra khi lưu bài viết');
    });
}

// Submit comment
function submitComment(postId) {
    // Không thực hiện bất kỳ hành động nào, vì form submit đã được xử lý trong initializeCommentForms
    console.log("submitComment được gọi, nhưng không thực hiện hành động gì vì đã có xử lý trong initializeCommentForms");
    return false;
}

// Delete post
function deletePost(postId) {
    if (confirm('Bạn có chắc chắn muốn xóa bài viết này?')) {
        fetch(`/api/posts/${postId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                const postElement = document.querySelector(`#post-${postId}`);
                postElement.remove();
            }
        })
        .catch(error => console.error('Error:', error));
    }
}

// WebSocket connection for real-time features
let chatSocket = null;

function connectWebSocket(roomId) {
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    chatSocket = new WebSocket(
        `${wsScheme}://${window.location.host}/ws/chat/${roomId}/`
    );

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        handleWebSocketMessage(data);
    };

    chatSocket.onclose = function(e) {
        console.log('Chat socket closed unexpectedly');
        setTimeout(function() {
            connectWebSocket(roomId);
        }, 3000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'chat_message':
            appendMessage(data.message);
            break;
        case 'notification':
            showNotification(data.notification);
            break;
        case 'typing':
            updateTypingStatus(data.user, data.typing);
            break;
    }
}

// Notification permission
function requestNotificationPermission() {
    if ('Notification' in window) {
        Notification.requestPermission().then(function(permission) {
            if (permission === 'granted') {
                subscribeToNotifications();
            }
        });
    }
}

function subscribeToNotifications() {
    navigator.serviceWorker.ready.then(function(registration) {
        return registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
        });
    }).then(function(subscription) {
        // Send subscription to server
        return fetch('/api/notifications/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                subscription: subscription.toJSON()
            })
        });
    });
}

// Infinite scroll
let loading = false;
let page = 1;

window.addEventListener('scroll', function() {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000) {
        // Xác định loại trang đang hiển thị
        const isProfilePage = window.location.pathname.startsWith('/users/');
        
        if (isProfilePage) {
            loadMoreProfilePosts();
        } else {
            loadMoreContent();
        }
    }
});

function loadMoreProfilePosts() {
    if (loading) return;
    loading = true;
    
    // Lấy username từ URL path
    const pathSegments = window.location.pathname.split('/');
    const username = pathSegments[2]; // users/{username}/
    
    const loadMoreButton = document.querySelector('#load-more-button');
    if (!loadMoreButton) return;
    
    const currentPage = parseInt(loadMoreButton.getAttribute('data-current-page')) || 1;
    const nextPage = currentPage + 1;
    
    fetch(`/api/posts/list/?page=${nextPage}&username=${username}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.posts && data.posts.length > 0) {
            const postsContainer = document.querySelector('#posts-container');
            data.posts.forEach(post => {
                const postElement = createPostElement(post);
                postsContainer.appendChild(postElement);
            });
            
            loadMoreButton.setAttribute('data-current-page', nextPage);
            
            if (!data.has_next) {
                loadMoreButton.style.display = 'none';
            }
        } else {
            loadMoreButton.style.display = 'none';
        }
        loading = false;
    })
    .catch(error => {
        console.error('Error loading more profile posts:', error);
        loading = false;
    });
}

function loadMoreContent() {
    if (loading) return;
    loading = true;
    
    const loadMoreButton = document.querySelector('#load-more-button');
    if (!loadMoreButton) return;
    
    const currentPage = parseInt(loadMoreButton.getAttribute('data-current-page')) || 1;
    const nextPage = currentPage + 1;
    
    fetch(`/api/posts/list/?page=${nextPage}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.posts && data.posts.length > 0) {
            const postsContainer = document.querySelector('#posts-container');
            data.posts.forEach(post => {
                const postElement = createPostElement(post);
                postsContainer.appendChild(postElement);
            });
            
            loadMoreButton.setAttribute('data-current-page', nextPage);
            
            if (!data.has_next) {
                loadMoreButton.style.display = 'none';
            }
        } else {
            loadMoreButton.style.display = 'none';
        }
        loading = false;
    })
    .catch(error => {
        console.error('Error loading more posts:', error);
        loading = false;
    });
}

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Hàm tạo phần tử comment
function createCommentElement(comment) {
    const div = document.createElement('div');
    div.className = 'comment mb-2' + (comment.parent ? ' ms-4' : '');
    div.id = `comment-${comment.id}`;
    if (comment.parent) {
        div.setAttribute('data-parent-id', comment.parent.id);
    }
    
    // Kiểm tra xem người dùng hiện tại có phải là tác giả của comment không
    const currentUserId = getCurrentUserId(); // Bạn cần triển khai hàm này
    const isAuthor = currentUserId && currentUserId == comment.author_id;
    
    div.innerHTML = `
        <div class="d-flex">
            <img src="${comment.author_avatar || '/static/images/default-avatar.png'}" 
                 class="rounded-circle me-2" 
                 style="width: 32px; height: 32px;">
            <div class="flex-grow-1">
                <div>
                    <a href="/users/${comment.author_username}/" class="fw-bold text-dark text-decoration-none">
                        ${comment.author_username}
                    </a>
                    ${comment.parent ? `<span class="text-muted mx-1">trả lời</span>
                    <a href="/users/${comment.parent.author_username}/" class="fw-bold text-dark text-decoration-none">
                        ${comment.parent.author_username}
                    </a>` : ''}
                    <span class="text-muted ms-2">${comment.text}</span>
                </div>
                <div class="mt-1">
                    <small class="text-muted">${comment.created_at}</small>
                    <button class="btn btn-link btn-sm p-0 text-muted reply-button ms-2" 
                            data-username="${comment.author_username}"
                            data-post-id="${comment.post_id}"
                            data-comment-id="${comment.id}">
                        <i class="fas fa-reply"></i> Trả lời
                    </button>
                    ${isAuthor ? `
                    <button class="btn btn-link btn-sm p-0 text-danger delete-comment-button ms-2" 
                            onclick="deleteComment(${comment.id})">
                        <i class="fas fa-trash"></i> Xóa
                    </button>` : ''}
                </div>
            </div>
        </div>
    `;
    
    // Thêm event listener cho nút reply
    const replyButton = div.querySelector('.reply-button');
    replyButton.addEventListener('click', function() {
        const postId = this.getAttribute('data-post-id');
        const username = this.getAttribute('data-username');
        const commentId = this.getAttribute('data-comment-id');
        showReplyForm(postId, username, commentId);
    });
    
    return div;
}

// Hàm hiển thị form reply
function showReplyForm(postId, username, commentId) {
    const replyInfo = document.querySelector(`#post-${postId} .reply-info`);
    const replyUsername = replyInfo.querySelector('.reply-to-username');
    replyUsername.textContent = username;
    replyInfo.classList.remove('d-none');
    
    // Lưu comment ID vào form
    const form = document.querySelector(`#post-${postId} .comment-form`);
    form.setAttribute('data-parent-id', commentId);
    
    // Focus vào input
    const input = document.querySelector(`#post-${postId} .comment-input`);
    input.focus();
}

// Create post element
function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'post-card';
    div.id = `post-${post.id}`;
    // Add post HTML structure here
    return div;
}

// Setup AJAX CSRF token
const csrftoken = getCookie('csrftoken');
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

// Notifications
function loadUnreadNotificationsCount() {
    $.get('/api/notifications/unread-count/', function(data) {
        const count = data.count;
        const badge = $('#unread-notifications');
        if (count > 0) {
            badge.text(count).show();
        } else {
            badge.hide();
        }
    });
}

// Biến để kiểm tra xem đã khởi tạo comment forms hay chưa
let commentFormsInitialized = false;

// Xử lý form bình luận - Cải tiến để chỉ chạy một lần
document.addEventListener('DOMContentLoaded', function() {
    // Kiểm tra xem đã khởi tạo chưa
    if (commentFormsInitialized) {
        console.log("DOMContentLoaded đã được xử lý trước đó, bỏ qua");
        return;
    }
    
    console.log("Bắt đầu xử lý DOMContentLoaded");
    commentFormsInitialized = true;
    
    // Xử lý các form bình luận
    initializeCommentForms();
    
    // Xử lý nút reply
    initializeReplyButtons();
    
    // Xử lý nút cancel reply
    initializeCancelReplyButtons();
    
    console.log("Xử lý DOMContentLoaded hoàn tất");
});

// Để debug các event listener đã được đăng ký
function logEventListeners(element) {
    console.log('Element:', element);
    console.log('ID:', element.id);
    console.log('Classes:', element.className);
    console.log('Data attributes:', element.dataset);
}

// Hàm khởi tạo form bình luận
function initializeCommentForms() {
    console.log("Bắt đầu khởi tạo form bình luận...");
    
    document.querySelectorAll('.add-comment-form').forEach(form => {
        // Tạo ID duy nhất cho form
        const formId = form.getAttribute('data-post-id') || Math.random().toString(36).substr(2, 9);
        const uniqueFormId = `comment-form-${formId}`;
        
        // Kiểm tra xem form đã được khởi tạo chưa
        if (form.getAttribute('data-initialized') === 'true' || window.Hoshi.processedEvents.has(uniqueFormId)) {
            console.log(`Form với post-id=${formId} đã được khởi tạo trước đó.`);
            return;
        }
        
        // Đánh dấu form đã được khởi tạo
        form.setAttribute('data-initialized', 'true');
        window.Hoshi.processedEvents.add(uniqueFormId);
        
        console.log(`Đăng ký event submit cho form với post-id=${formId}`);
        
        // Xử lý sự kiện submit với debounce để tránh trigger nhiều lần
        const handleSubmit = throttle(function(e) {
            console.log(`Form submit được kích hoạt cho post-id=${this.getAttribute('data-post-id')}`);
            e.preventDefault();
            
            const postId = this.getAttribute('data-post-id');
            const commentInput = this.querySelector('input[name="text"]');
            const text = commentInput.value.trim();
            const replyInfo = this.querySelector('.reply-info');
            const isReply = replyInfo && !replyInfo.classList.contains('d-none');
            let parentId = this.getAttribute('data-parent-id');
            
            if (!text) return;
            
            // Biến để chặn gửi nhiều lần
            if (this.getAttribute('data-submitting') === 'true') {
                console.log('Đã có một yêu cầu đang được xử lý, bỏ qua');
                return;
            }
            
            // Đánh dấu đang submit
            this.setAttribute('data-submitting', 'true');
            
            // Hiển thị loading
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
            
            // Tạo timestamp và request_id duy nhất
            const timestamp = Date.now();
            const requestId = `comment-${postId}-${timestamp}-${Math.random().toString(36).substring(2, 10)}`;
            
            // Ghi nhớ request ID này đã được gửi
            if (!window.Hoshi.sentCommentRequests) window.Hoshi.sentCommentRequests = new Set();
            window.Hoshi.sentCommentRequests.add(requestId);
            
            // Kiểm tra xem đã gửi request này chưa
            if (window.Hoshi.processedRequests.has(`${postId}-${text}-${parentId || ''}`)) {
                console.log('Request trùng lặp đã được gửi, bỏ qua');
                
                // Bỏ đánh dấu đang submit
                this.removeAttribute('data-submitting');
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                return;
            }
            
            // Đánh dấu request này đã được gửi
            window.Hoshi.processedRequests.add(`${postId}-${text}-${parentId || ''}`);
            
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
                    parent_id: parentId || null,
                    timestamp: timestamp,
                    request_id: requestId
                })
            })
            .then(response => response.json())
            .then(data => {
                // Bỏ đánh dấu đang submit
                this.removeAttribute('data-submitting');
                
                // Sau 3 giây, xóa request ID khỏi danh sách đã xử lý để cho phép submit lại
                setTimeout(() => {
                    if (window.Hoshi.processedRequests.has(`${postId}-${text}-${parentId || ''}`)) {
                        window.Hoshi.processedRequests.delete(`${postId}-${text}-${parentId || ''}`);
                    }
                }, 3000);
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                if (data.comment) {
                    // Kiểm tra xem có phải bình luận trùng lặp không 
                    if (!data.comment.is_duplicate) {
                        // Thêm bình luận mới vào DOM
                        addCommentToDOM(data.comment, postId, isReply, parentId);
                        
                        // Cập nhật số lượng bình luận
                        updateCommentCount(postId);
                    } else {
                        console.log('Bình luận này là bản trùng lặp, không hiển thị lại');
                    }
                    
                    // Xóa nội dung input và ẩn thông tin trả lời
                    commentInput.value = '';
                    if (replyInfo) replyInfo.classList.add('d-none');
                    form.removeAttribute('data-parent-id');
                } else {
                    alert(data.error || 'Có lỗi xảy ra khi thêm bình luận');
                }
            })
            .catch(error => {
                // Bỏ đánh dấu đang submit
                this.removeAttribute('data-submitting');
                
                // Xóa request ID khỏi danh sách đã xử lý để cho phép submit lại
                if (window.Hoshi.processedRequests.has(`${postId}-${text}-${parentId || ''}`)) {
                    window.Hoshi.processedRequests.delete(`${postId}-${text}-${parentId || ''}`);
                }
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                console.error('Error:', error);
                alert('Có lỗi xảy ra khi thêm bình luận');
            });
        }, 500); // 500ms throttle time để ngăn double-click submit
        
        // Sử dụng safeAddEventListener thay vì addEventListener trực tiếp
        safeAddEventListener(form, 'submit', handleSubmit, uniqueFormId);
    });
    
    console.log("Khởi tạo form bình luận hoàn tất");
}

// Hàm cập nhật số lượng bình luận
function updateCommentCount(postId) {
    const commentCountElements = document.querySelectorAll(`.comment-button[data-post-id="${postId}"] span, .comment-count[data-post-id="${postId}"]`);
    commentCountElements.forEach(element => {
        if (element) {
            const currentCount = parseInt(element.textContent) || 0;
            element.textContent = currentCount + 1;
        }
    });
}

// Hàm khởi tạo nút reply
function initializeReplyButtons() {
    document.querySelectorAll('.reply-button').forEach(button => {
        // Tạo ID duy nhất cho button dựa trên data và vị trí
        const username = button.getAttribute('data-username') || '';
        const postId = button.getAttribute('data-post-id') || '';
        const commentId = button.getAttribute('data-comment-id') || '';
        const buttonId = `reply-button-${postId}-${username}-${commentId}`;
        
        // Kiểm tra xem đã xử lý chưa
        if (window.Hoshi.processedEvents.has(buttonId)) {
            return;
        }
        
        // Xử lý sự kiện click
        const handleClick = function() {
            const username = this.getAttribute('data-username');
            const postId = this.getAttribute('data-post-id');
            const commentId = this.closest('.comment, .reply-comment')?.id?.replace('comment-', '') || 
                            this.getAttribute('data-comment-id');
            
            if (!username || !postId) return;
            
            const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
            if (!form) {
                console.error(`Không tìm thấy form cho post ID ${postId}`);
                return;
            }
            
            const replyInfo = form.querySelector('.reply-info');
            if (!replyInfo) {
                console.error(`Không tìm thấy reply-info trong form cho post ID ${postId}`);
                return;
            }
            
            const replyUsername = replyInfo.querySelector('.reply-to-username');
            
            // Hiển thị thông tin đang trả lời
            replyInfo.classList.remove('d-none');
            replyUsername.textContent = username;
            
            // Lưu ID của comment cha
            if (commentId) {
                form.setAttribute('data-parent-id', commentId);
            }
            
            // Focus vào input
            const input = form.querySelector('input[name="text"]');
            if (input) input.focus();
        };
        
        // Sử dụng safeAddEventListener
        safeAddEventListener(button, 'click', handleClick, buttonId);
    });
}

// Hàm khởi tạo nút cancel reply
function initializeCancelReplyButtons() {
    document.querySelectorAll('.cancel-reply').forEach(button => {
        button.addEventListener('click', function() {
            const replyInfo = this.closest('.reply-info');
            const form = replyInfo.closest('.add-comment-form');
            const input = form.querySelector('input[name="text"]');
            
            // Ẩn thông tin trả lời
            replyInfo.classList.add('d-none');
            
            // Xóa reference đến comment cha
            form.removeAttribute('data-parent-id');
            
            // Focus vào input
            input.focus();
        });
    });
}

// Debug: Log thông tin comment khi thêm
function debugLogComment(comment, postId, isReply, parentId) {
    console.group('Thêm Comment Mới');
    console.log('Comment:', comment);
    console.log('Post ID:', postId);
    console.log('Is Reply:', isReply);
    console.log('Parent ID:', parentId);
    
    // Kiểm tra các phần tử DOM
    const postElement = document.querySelector(`.card[data-post-id="${postId}"]`);
    console.log('Post Element:', postElement);
    
    const commentsSection = postElement ? postElement.querySelector('.comments-section') : null;
    console.log('Comments Section:', commentsSection);
    
    console.groupEnd();
}

// Ghi đè hàm addCommentToDOM để thêm debug
function addCommentToDOM(comment, postId, isReply, parentId) {
    console.log('addCommentToDOM được gọi với comment ID:', comment.id);
    
    // Kiểm tra chính xác xem comment đã tồn tại trong DOM chưa
    // Tìm kiếm bất kỳ phần tử nào có ID là comment-ID, bất kể là comment hay reply
    const existingComment = document.getElementById(`comment-${comment.id}`);
    if (existingComment) {
        console.log(`Comment với ID ${comment.id} đã tồn tại trong DOM, bỏ qua.`);
        return;
    }
    
    // Chuẩn hóa dữ liệu comment từ API
    const normalizedComment = {
        id: comment.id,
        text: comment.text,
        created_at: comment.created_at,
        author: {
            username: comment.author ? comment.author.username : comment.author_username,
            avatar: comment.author ? comment.author.avatar : comment.author_avatar
        }
    };
    
    console.log('Normalized Comment:', normalizedComment);
    
    // Tìm card chứa bài viết
    const postCard = document.querySelector(`#post-${postId}, .card[id="post-${postId}"]`);
    if (!postCard) {
        console.error(`Không tìm thấy bài viết với ID ${postId}`);
        return;
    }
    
    // Tạo HTML cho comment mới
    const commentHTML = `
        <div class="comment mb-2" id="comment-${normalizedComment.id}" data-comment-id="${normalizedComment.id}">
            <div class="d-flex justify-content-between">
                <div>
                    <a href="/users/${normalizedComment.author.username}/" 
                       class="text-dark text-decoration-none fw-bold">
                        ${normalizedComment.author.username}
                    </a>
                    ${normalizedComment.text}
                </div>
                <div class="dropdown">
                    <button class="btn btn-link btn-sm p-0 text-muted dropdown-toggle" 
                            type="button" 
                            data-bs-toggle="dropdown" 
                            aria-expanded="false">
                        <i class="fas fa-ellipsis-h"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li>
                            <button class="dropdown-item reply-button" 
                                    data-username="${normalizedComment.author.username}"
                                    data-post-id="${postId}"
                                    data-comment-id="${normalizedComment.id}">
                                <i class="fas fa-reply me-2"></i>Trả lời
                            </button>
                        </li>
                        <li>
                            <button class="dropdown-item text-danger" 
                                   onclick="deleteComment(${normalizedComment.id})">
                                <i class="fas fa-trash-alt me-2"></i>Xóa
                            </button>
                        </li>
                    </ul>
                </div>
            </div>
            <div class="text-muted small">
                vừa xong · 
                <button class="btn btn-link btn-sm p-0 text-muted like-comment-button" 
                        data-comment-id="${normalizedComment.id}">
                    <span>Thích</span>
                </button>
                <span class="ms-1">·</span>
                <button class="btn btn-link btn-sm p-0 text-muted reply-button ms-1" 
                        data-username="${normalizedComment.author.username}"
                        data-post-id="${postId}"
                        data-comment-id="${normalizedComment.id}">
                    Trả lời
                </button>
            </div>
        </div>
    `;
    
    // Tìm section comments
    let commentsSection = postCard.querySelector('.overflow-auto');
    
    if (!commentsSection) {
        console.error('Không tìm thấy phần hiển thị comments trong bài viết');
        return;
    }
    
    // Tìm vị trí chèn bình luận dựa vào parent
    if (isReply && parentId) {
        // Tìm vị trí để thêm reply
        const parentComment = document.getElementById(`comment-${parentId}`);
        
        if (parentComment) {
            let repliesSection = parentComment.querySelector('.comment-replies');
            if (!repliesSection) {
                // Tạo section replies nếu chưa có
                repliesSection = document.createElement('div');
                repliesSection.className = 'comment-replies ps-4 mt-2';
                parentComment.appendChild(repliesSection);
            }
            
            // Thêm reply vào cuối danh sách replies
            repliesSection.insertAdjacentHTML('beforeend', commentHTML.replace('comment mb-2', 'reply-comment mb-2'));
        } else {
            // Nếu không tìm thấy comment cha, thêm như comment thông thường
            insertCommentIntoMainSection(commentsSection, commentHTML);
        }
    } else {
        // Thêm comment mới vào phần comments chính
        insertCommentIntoMainSection(commentsSection, commentHTML);
    }
    
    // Khởi tạo các event handlers cho comment mới
    const newComment = document.getElementById(`comment-${normalizedComment.id}`);
    if (newComment) {
        initializeNewCommentButtons(newComment);
    } else {
        console.error(`Không thể tìm thấy comment đã thêm với ID ${normalizedComment.id}`);
    }
}

// Hàm thêm comment vào phần comments chính
function insertCommentIntoMainSection(commentsSection, commentHTML) {
    // Tìm danh sách comments
    const commentsList = commentsSection.querySelector('.comments-section');
    
    if (commentsList) {
        // Nếu tìm thấy danh sách, thêm vào đầu
        commentsList.insertAdjacentHTML('afterbegin', commentHTML);
    } else {
        // Nếu không tìm thấy danh sách, thêm trực tiếp vào phần comments
        // Kiểm tra xem có thông báo "Chưa có bình luận nào" không
        const emptyMessage = commentsSection.querySelector('p.text-muted.text-center');
        if (emptyMessage) {
            // Thay thế thông báo bằng comment
            emptyMessage.remove();
        }
        
        // Thêm vào đầu danh sách
        commentsSection.insertAdjacentHTML('afterbegin', commentHTML);
    }
}

// Hàm khởi tạo các nút cho comment mới
function initializeNewCommentButtons(commentElement) {
    // Khởi tạo nút Reply
    const replyButtons = commentElement.querySelectorAll('.reply-button');
    replyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const username = this.getAttribute('data-username');
            const postId = this.getAttribute('data-post-id');
            const commentId = this.getAttribute('data-comment-id') || 
                              this.closest('.comment, .reply-comment')?.getAttribute('data-comment-id');
            
            if (!username || !postId) return;
            
            const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
            const replyInfo = form.querySelector('.reply-info');
            const replyUsername = replyInfo.querySelector('.reply-to-username');
            
            replyInfo.classList.remove('d-none');
            replyUsername.textContent = username;
            
            if (commentId) {
                form.setAttribute('data-parent-id', commentId);
            }
            
            const input = form.querySelector('input[name="text"]');
            input.focus();
        });
    });
    
    // Khởi tạo nút Like
    const likeButtons = commentElement.querySelectorAll('.like-comment-button');
    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const commentId = this.getAttribute('data-comment-id');
            if (!commentId) return;
            
            fetch(`/api/posts/comments/${commentId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                const textElement = button.querySelector('span');
                
                if (data.status === 'liked') {
                    textElement.textContent = 'Đã thích';
                    textElement.classList.add('text-primary');
                } else {
                    textElement.textContent = 'Thích';
                    textElement.classList.remove('text-primary');
                }
                
                // Cập nhật số lượng likes nếu có
                if (data.likes_count > 0) {
                    let likesCountElement = commentElement.querySelector('.comment-likes-count');
                    if (!likesCountElement) {
                        const likesCountHTML = `
                            <span class="ms-2">
                                <i class="fas fa-heart text-danger small"></i>
                                <span class="comment-likes-count" data-comment-id="${commentId}">${data.likes_count}</span>
                            </span>
                        `;
                        button.closest('.text-muted.small').insertAdjacentHTML('beforeend', likesCountHTML);
                    } else {
                        likesCountElement.textContent = data.likes_count;
                    }
                }
            })
            .catch(error => {
                console.error('Lỗi khi thích bình luận:', error);
            });
        });
    });
}

// Hiển thị thông tin bài viết đã lưu
function displayFileNames(input) {
    const selectedFiles = document.getElementById('selectedFiles');
    if (input.files.length > 0) {
        const fileNames = Array.from(input.files)
            .map(file => file.name)
            .join(', ');
        selectedFiles.textContent = fileNames;
    } else {
        selectedFiles.textContent = '';
    }
}

// Hàm xóa comment
function deleteComment(commentId) {
    if (!confirm('Bạn có chắc chắn muốn xóa bình luận này?')) {
        return;
    }
    
    fetch(`/api/posts/comments/${commentId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Xóa comment khỏi DOM
            const commentElement = document.getElementById(`comment-${commentId}`);
            if (commentElement) {
                // Nếu comment là parent, xóa cả các reply của nó
                const replies = commentElement.parentNode.querySelectorAll(`[data-parent-id="${commentId}"]`);
                replies.forEach(reply => reply.remove());
                
                // Xóa comment
                commentElement.remove();
                
                // Cập nhật số lượng comment
                const postId = commentElement.closest('.card').id.replace('post-', '');
                const commentCountElement = document.querySelector(`#post-${postId} .comment-count`);
                if (commentCountElement) {
                    const newCount = parseInt(commentCountElement.textContent) - 1;
                    commentCountElement.textContent = newCount >= 0 ? newCount : 0;
                }
            }
        } else {
            alert(data.error || 'Có lỗi xảy ra khi xóa bình luận');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Có lỗi xảy ra khi xóa bình luận');
    });
}

// Hàm để lấy ID của người dùng hiện tại
function getCurrentUserId() {
    // Thử lấy từ một meta tag
    const metaUserId = document.querySelector('meta[name="user-id"]');
    if (metaUserId) return metaUserId.getAttribute('content');
    
    // Thử lấy từ một data attribute trên body hoặc html
    const bodyUserId = document.body.getAttribute('data-user-id');
    if (bodyUserId) return bodyUserId;
    
    // Nếu không tìm thấy, trả về null
    return null;
}

// Like comment
function likeComment(commentId) {
    fetch(`/api/posts/comments/${commentId}/like/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const commentLikeButtons = document.querySelectorAll(`.like-comment-button[data-comment-id="${commentId}"]`);
        const commentLikesCountElements = document.querySelectorAll(`.comment-likes-count[data-comment-id="${commentId}"]`);
        
        commentLikeButtons.forEach(button => {
            const likeText = button.querySelector('span');
            if (data.status === 'liked') {
                likeText.textContent = 'Đã thích';
                likeText.classList.add('text-primary');
            } else if (data.status === 'unliked') {
                likeText.textContent = 'Thích';
                likeText.classList.remove('text-primary');
            }
        });

        commentLikesCountElements.forEach(likeCountElement => {
            if (data.likes_count > 0) {
                likeCountElement.textContent = data.likes_count;
                likeCountElement.closest('.comment').querySelector('.comment-likes-count-container').style.display = 'inline';
            } else {
                likeCountElement.closest('.comment').querySelector('.comment-likes-count-container').style.display = 'none';
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Có lỗi xảy ra khi thích bình luận');
    });
} 