// Initialize Bootstrap tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
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
    const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
    if (!form) {
        console.error(`Không tìm thấy form comment cho bài viết ${postId}`);
        return;
    }

    const commentInput = form.querySelector('.comment-input');
    const text = commentInput.value.trim();
    const replyInfo = form.querySelector('.reply-info');
    const parentId = form.getAttribute('data-parent-id');
    
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
                parent_id: parentId || null
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || 'Lỗi không xác định');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.comment) {
                // Thêm comment mới vào DOM
                addCommentToDOM(data.comment, postId, !!parentId, parentId);
                
                // Xóa nội dung input và ẩn thông tin trả lời
                commentInput.value = '';
                if (replyInfo) replyInfo.classList.add('d-none');
                form.removeAttribute('data-parent-id');
            } else {
                alert(data.error || 'Có lỗi xảy ra khi thêm bình luận');
            }
        })
        .catch(error => {
            console.error('Lỗi khi thêm bình luận:', error);
            alert(error.message || 'Có lỗi xảy ra khi thêm bình luận');
        });
    }
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
        loadMoreContent();
    }
});

function loadMoreContent() {
    if (loading) return;
    
    loading = true;
    const loadingIndicator = document.querySelector('.loading-indicator');
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    
    fetch(`/api/posts/?page=${page + 1}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.posts.length > 0) {
            data.posts.forEach(post => {
                const postElement = createPostElement(post);
                document.querySelector('.posts-container').appendChild(postElement);
            });
            page += 1;
        }
        loading = false;
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    })
    .catch(error => {
        console.error('Error:', error);
        loading = false;
        if (loadingIndicator) loadingIndicator.style.display = 'none';
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

// Initialize components when document is ready
$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
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

    // Xử lý nút reply comment
    document.querySelectorAll('.reply-button').forEach(button => {
        button.addEventListener('click', function() {
            const username = this.getAttribute('data-username');
            const postId = this.getAttribute('data-post-id');
            if (username && postId) {
                showReplyForm(postId, username, this.getAttribute('data-comment-id'));
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

    // Thêm event listener cho các form comment
    const commentForms = document.querySelectorAll('.add-comment-form');
    
    commentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const postId = this.getAttribute('data-post-id');
            submitComment(postId);
        });
    });
});

// Xử lý nút trả lời bình luận
document.querySelectorAll('.reply-button').forEach(button => {
    button.addEventListener('click', function() {
        const username = this.getAttribute('data-username');
        const postId = this.getAttribute('data-post-id');
        const commentForm = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
        const commentInput = commentForm.querySelector('input[name="text"]');
        const replyInfo = commentForm.querySelector('.reply-info');
        const replyToUsername = replyInfo.querySelector('.reply-to-username');
        
        // Hiển thị thông tin đang trả lời
        replyInfo.classList.remove('d-none');
        replyToUsername.textContent = username;
        
        // Thêm @username vào input nếu chưa có
        if (!commentInput.value.startsWith(`@${username} `)) {
            commentInput.value = `@${username} ${commentInput.value}`;
        }
        
        // Focus vào input
        commentInput.focus();
        
        // Đặt con trỏ ở cuối text
        const inputLength = commentInput.value.length;
        commentInput.setSelectionRange(inputLength, inputLength);
    });
});

// Xử lý nút hủy trả lời
document.querySelectorAll('.cancel-reply').forEach(button => {
    button.addEventListener('click', function() {
        const replyInfo = this.closest('.reply-info');
        const commentForm = this.closest('.add-comment-form');
        const commentInput = commentForm.querySelector('input[name="text"]');
        const username = replyInfo.querySelector('.reply-to-username').textContent;
        
        // Ẩn thông tin đang trả lời
        replyInfo.classList.add('d-none');
        
        // Xóa @username khỏi input
        commentInput.value = commentInput.value.replace(`@${username} `, '');
        
        // Focus vào input
        commentInput.focus();
    });
});

// Xử lý form bình luận
document.querySelectorAll('.add-comment-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const postId = this.getAttribute('data-post-id');
        const commentInput = this.querySelector('input[name="text"]');
        const text = commentInput.value.trim();
        const replyInfo = this.querySelector('.reply-info');
        const isReply = !replyInfo.classList.contains('d-none');
        let parentId = null;
        
        // Nếu là trả lời, lấy id của comment cha
        if (isReply) {
            const username = replyInfo.querySelector('.reply-to-username').textContent;
            // Lấy comment-id từ nút reply được click
            const replyButton = document.querySelector('.reply-button[data-username="' + username + '"][data-comment-id]');
            if (replyButton) {
                parentId = replyButton.getAttribute('data-comment-id');
            }
        }
        
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
                if (data.comment) {
                    // Thêm bình luận mới vào DOM
                    addCommentToDOM(data.comment, postId, isReply, parentId);
                    
                    // Cập nhật số lượng bình luận
                    const commentCountElement = document.querySelector(`.comment-button[onclick*="comment-input-${postId}"] span`);
                    if (commentCountElement) {
                        commentCountElement.textContent = parseInt(commentCountElement.textContent) + 1;
                    }
                    
                    // Xóa nội dung input và ẩn thông tin trả lời
                    commentInput.value = '';
                    replyInfo.classList.add('d-none');
                } else {
                    alert(data.error || 'Có lỗi xảy ra khi thêm bình luận');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Có lỗi xảy ra khi thêm bình luận');
            });
        }
    });
});

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
    // Debug log
    debugLogComment(comment, postId, isReply, parentId);
    
    // Phần code cũ của hàm addCommentToDOM
    const postElement = document.querySelector(`.card[data-post-id="${postId}"]`);
    
    if (!postElement) {
        console.error(`Không tìm thấy bài viết với ID ${postId}`);
        return;
    }
    
    // Phần còn lại của hàm không thay đổi
    const commentHTML = `
        <div class="comment mb-2" id="comment-${comment.id}">
            <div class="d-flex">
                <img src="${comment.author.avatar || '/static/images/default-avatar.png'}" 
                     class="rounded-circle me-2" 
                     style="width: 32px; height: 32px;">
                <div class="flex-grow-1">
                    <div>
                        <a href="/users/${comment.author.username}/" 
                           class="fw-bold text-dark text-decoration-none">
                            ${comment.author.username}
                        </a>
                        ${parentId ? `<span class="text-muted mx-1">trả lời</span>` : ''}
                        <span class="text-muted ms-2">${comment.text}</span>
                    </div>
                    <div class="mt-1">
                        <small class="text-muted">${new Date(comment.created_at).toLocaleString()}</small>
                        <button class="btn btn-link btn-sm p-0 text-muted reply-button ms-2" 
                                data-username="${comment.author.username}"
                                data-post-id="${postId}"
                                data-comment-id="${comment.id}">
                            <i class="fas fa-reply"></i> Trả lời
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Tìm section comments
    let commentsSection = postElement.querySelector('.comments-section');
    
    // Nếu chưa có section comments, tạo mới
    if (!commentsSection) {
        commentsSection = document.createElement('div');
        commentsSection.className = 'comments-section';
        
        // Tìm card body cuối cùng để chèn
        const cardBody = postElement.querySelector('.card-body:last-child');
        if (cardBody) {
            cardBody.insertBefore(commentsSection, cardBody.lastElementChild);
        }
    }
    
    // Thêm comment vào đầu danh sách
    commentsSection.insertAdjacentHTML('afterbegin', commentHTML);
    
    // Cập nhật số lượng comment
    const commentCountElement = postElement.querySelector('.comment-button span');
    if (commentCountElement) {
        const currentCount = parseInt(commentCountElement.textContent) || 0;
        commentCountElement.textContent = currentCount + 1;
    }
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
    fetch(`/api/comments/${commentId}/like/`, {
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