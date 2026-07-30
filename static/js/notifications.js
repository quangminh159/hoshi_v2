// Notifications Websocket Connection
let wsReconnectAttempts = 0;
const WS_MAX_RECONNECT = 3;
let wsDisabled = false;

document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('user-authenticated') && !wsDisabled) {
        connectWebSocket();
    }

    setupNotificationInteractions();
});

function connectWebSocket() {
    if (wsDisabled || wsReconnectAttempts >= WS_MAX_RECONNECT) {
        return;
    }

    const userId = document.body.dataset.userId;
    if (!userId) {
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const host = window.location.host;
    const wsUrl = `${protocol}${host}/ws/notifications/${userId}/`;

    try {
        const socket = new WebSocket(wsUrl);

        socket.addEventListener('open', () => {
            wsReconnectAttempts = 0;
        });

        socket.addEventListener('message', (event) => {
            const data = JSON.parse(event.data);
            handleNotification(data);
        });

        socket.addEventListener('close', () => {
            wsReconnectAttempts += 1;
            if (wsReconnectAttempts >= WS_MAX_RECONNECT) {
                wsDisabled = true;
                console.warn('WebSocket thông báo không khả dụng. Chạy server bằng: python -m daphne -p 8000 hoshi.asgi:application');
                return;
            }
            setTimeout(connectWebSocket, 5000 * wsReconnectAttempts);
        });

        socket.addEventListener('error', () => {
            // close handler manages retry
        });
    } catch (error) {
        console.error('Error creating WebSocket connection:', error);
    }
}

function handleNotification(data) {
    if (typeof data.unread_count !== 'undefined') {
        updateNotificationCount(data.unread_count);
    }

    if (data.notification && Object.keys(data.notification).length > 0) {
        addNotificationToList(data.notification);
        showToast(data.notification);
    }
}

function updateNotificationCount(count) {
    const badge = document.getElementById('notification-count');
    if (!badge) return;

    badge.textContent = count;

    if (count > 0) {
        badge.style.display = '';
    } else {
        badge.style.display = 'none';
    }
}

function getNotificationLink(notification) {
    if (notification.link && notification.link !== '#') {
        return notification.link;
    }

    const postTypes = ['like', 'like_post', 'comment', 'comment_reply', 'mention', 'share'];
    if (postTypes.includes(notification.notification_type) && notification.post_id) {
        return `/posts/${notification.post_id}/`;
    }
    if (notification.notification_type === 'follow' && notification.sender_username) {
        return `/users/${notification.sender_username}/`;
    }
    if (notification.notification_type === 'message' && notification.conversation_id) {
        return `/chat/conversations/${notification.conversation_id}/`;
    }
    return '#';
}

function getNotificationTitle(notification) {
    switch (notification.notification_type) {
        case 'like':
        case 'like_post':
            return 'Ai đó thích bài viết của bạn';
        case 'comment':
        case 'comment_reply':
            return 'Bình luận mới';
        case 'follow':
            return 'Người theo dõi mới';
        case 'mention':
            return 'Bạn được nhắc đến';
        case 'message':
            return 'Tin nhắn mới';
        case 'share':
            return 'Bài viết được chia sẻ';
        default:
            return 'Thông báo mới';
    }
}

function getNotificationText(notification) {
    return notification.text || getNotificationTitle(notification);
}

function addNotificationToList(notification) {
    const notificationList = document.querySelector('.notification-list');
    if (!notificationList || !notification.id) return;

    const emptyState = notificationList.querySelector('.text-center.text-muted');
    if (emptyState) {
        emptyState.remove();
    }

    const link = getNotificationLink(notification);
    const notificationItem = document.createElement('a');
    notificationItem.href = link;
    notificationItem.className = 'notification-item p-3 border-bottom bg-light text-decoration-none text-body d-block';
    notificationItem.dataset.id = notification.id;
    notificationItem.dataset.link = link;

    notificationItem.innerHTML = `
        <div class="d-flex">
            <img src="${notification.sender_avatar || '/static/img/default-avatar.png'}" class="rounded-circle me-2" width="40" height="40" alt="${notification.sender_username || 'User'}">
            <div>
                <p class="mb-1">${getNotificationText(notification)}</p>
                <small class="text-muted">vừa mới</small>
            </div>
        </div>
    `;

    notificationList.insertBefore(notificationItem, notificationList.firstChild);

    const items = notificationList.querySelectorAll('.notification-item');
    if (items.length > 5) {
        for (let i = 5; i < items.length; i++) {
            items[i].remove();
        }
    }
}

function showToast(notification) {
    let toastContainer = document.querySelector('.toast-container');

    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    const link = getNotificationLink(notification);
    const notificationText = getNotificationText(notification);
    const notificationTitle = getNotificationTitle(notification);

    toastEl.innerHTML = `
        <div class="toast-header">
            <img src="${notification.sender_avatar || '/static/img/default-avatar.png'}" class="rounded me-2" width="20" height="20" alt="${notification.sender_username || 'User'}">
            <strong class="me-auto">${notificationTitle}</strong>
            <small>vừa mới</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${link !== '#'
                ? `<a href="${link}" class="text-decoration-none text-body">${notificationText}</a>`
                : notificationText}
        </div>
    `;

    toastContainer.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl);
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

function markNotificationAsRead(notificationEl) {
    const notificationId = notificationEl.dataset.id;
    if (!notificationId) return;

    fetch(`/notifications/mark-as-read/${notificationId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        keepalive: true,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            notificationEl.classList.remove('bg-light');

            const badge = document.getElementById('notification-count');
            if (badge && badge.style.display !== 'none') {
                const currentCount = parseInt(badge.textContent, 10) || 0;
                if (currentCount > 0) {
                    updateNotificationCount(currentCount - 1);
                }
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

function setupNotificationInteractions() {
    const markAllReadBtn = document.querySelector('.mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function(e) {
            e.preventDefault();

            fetch(this.href, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelectorAll('.notification-item, .list-group-item[data-id]').forEach(item => {
                        item.classList.remove('bg-light');
                    });
                    updateNotificationCount(0);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    document.addEventListener('click', function(e) {
        const notificationItem = e.target.closest('.notification-item[data-id], .list-group-item[data-id]');
        if (!notificationItem) return;

        markNotificationAsRead(notificationItem);
    });
}

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
