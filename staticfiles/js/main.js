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
        if (data.status === 'success') {
            const likeButton = document.querySelector(`#post-${postId} .like-button`);
            const likeCount = document.querySelector(`#post-${postId} .like-count`);
            
            if (data.liked) {
                likeButton.classList.add('text-danger');
                likeCount.textContent = parseInt(likeCount.textContent) + 1;
            } else {
                likeButton.classList.remove('text-danger');
                likeCount.textContent = parseInt(likeCount.textContent) - 1;
            }
        }
    })
    .catch(error => console.error('Error:', error));
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
        if (data.status === 'success') {
            const saveButton = document.querySelector(`#post-${postId} .save-button`);
            
            if (data.saved) {
                saveButton.classList.add('text-primary');
            } else {
                saveButton.classList.remove('text-primary');
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Submit comment
function submitComment(postId) {
    const commentInput = document.querySelector(`#post-${postId} .comment-input`);
    const comment = commentInput.value.trim();
    
    if (comment) {
        fetch(`/api/posts/${postId}/comment/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: comment })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Add new comment to the list
                const commentsList = document.querySelector(`#post-${postId} .comments-list`);
                const newComment = createCommentElement(data.comment);
                commentsList.insertBefore(newComment, commentsList.firstChild);
                
                // Clear input
                commentInput.value = '';
                
                // Update comment count
                const commentCount = document.querySelector(`#post-${postId} .comment-count`);
                commentCount.textContent = parseInt(commentCount.textContent) + 1;
            }
        })
        .catch(error => console.error('Error:', error));
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

function createCommentElement(comment) {
    const div = document.createElement('div');
    div.className = 'comment d-flex align-items-start mb-2';
    div.innerHTML = `
        <img src="${comment.user.avatar}" alt="${comment.user.username}" class="rounded-circle me-2" width="32" height="32">
        <div class="flex-grow-1">
            <p class="mb-0">
                <a href="/users/${comment.user.username}" class="fw-bold text-decoration-none">${comment.user.username}</a>
                ${comment.text}
            </p>
            <small class="text-muted">${comment.created_at}</small>
        </div>
    `;
    return div;
}

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
}); 