// Notifications Websocket Connection
document.addEventListener('DOMContentLoaded', function() {
    // Only connect if user is authenticated
    if (document.body.classList.contains('user-authenticated')) {
        connectWebSocket();
    }

    // Setup mark as read functionality
    setupNotificationInteractions();
});

function connectWebSocket() {
    // Get the current user ID from the page (should be added in your template)
    const userId = document.body.dataset.userId;
    console.log("Connecting WebSocket with userId:", userId);
    if (!userId) {
        console.error("No userId found in body dataset");
        return;
    }

    // Create WebSocket connection based on secure or non-secure connection
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const host = window.location.host;
    const wsUrl = `${protocol}${host}/ws/notifications/${userId}/`;
    console.log("WebSocket URL:", wsUrl);
    
    try {
        const socket = new WebSocket(wsUrl);

        // Connection opened
        socket.addEventListener('open', (event) => {
            console.log('WebSocket connection established');
        });

        // Listen for messages
        socket.addEventListener('message', (event) => {
            console.log('WebSocket message received:', event.data);
            const data = JSON.parse(event.data);
            handleNotification(data);
        });

        // Connection closed
        socket.addEventListener('close', (event) => {
            console.log('WebSocket connection closed', event);
            // Try to reconnect after 5 seconds
            setTimeout(connectWebSocket, 5000);
        });

        // Error handling
        socket.addEventListener('error', (event) => {
            console.error('WebSocket error:', event);
        });
    } catch (error) {
        console.error('Error creating WebSocket connection:', error);
    }
}

function handleNotification(data) {
    // Update notification count
    updateNotificationCount(data.unread_count);

    // Add new notification to the list if we have a new one
    if (data.notification) {
        addNotificationToList(data.notification);
        
        // Show toast notification
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

function addNotificationToList(notification) {
    const notificationList = document.querySelector('.notification-list');
    if (!notificationList) return;

    // Check if we have the empty state message
    const emptyState = notificationList.querySelector('.text-center.text-muted');
    if (emptyState) {
        emptyState.remove();
    }

    // Create notification item
    const notificationItem = document.createElement('div');
    notificationItem.className = 'notification-item p-3 border-bottom bg-light';
    notificationItem.dataset.id = notification.id;

    let notificationText;
    switch(notification.notification_type) {
        case 'like':
            notificationText = `<a href="/profile/${notification.sender_username}/" class="fw-bold text-decoration-none">${notification.sender_username}</a> đã thích bài viết của bạn`;
            break;
        case 'comment':
            notificationText = `<a href="/profile/${notification.sender_username}/" class="fw-bold text-decoration-none">${notification.sender_username}</a> đã bình luận về bài viết của bạn`;
            break;
        case 'follow':
            notificationText = `<a href="/profile/${notification.sender_username}/" class="fw-bold text-decoration-none">${notification.sender_username}</a> đã theo dõi bạn`;
            break;
        case 'mention':
            notificationText = `<a href="/profile/${notification.sender_username}/" class="fw-bold text-decoration-none">${notification.sender_username}</a> đã nhắc đến bạn trong bài viết`;
            break;
        case 'message':
            notificationText = `<a href="/profile/${notification.sender_username}/" class="fw-bold text-decoration-none">${notification.sender_username}</a> đã gửi tin nhắn cho bạn`;
            break;
        default:
            notificationText = notification.text || 'Bạn có thông báo mới';
    }

    notificationItem.innerHTML = `
        <div class="d-flex">
            <img src="${notification.sender_avatar}" class="rounded-circle me-2" width="40" height="40" alt="${notification.sender_username}">
            <div>
                <p class="mb-1">${notificationText}</p>
                <small class="text-muted">vừa mới</small>
            </div>
        </div>
    `;

    // Add to the top of the list
    const firstItem = notificationList.firstChild;
    notificationList.insertBefore(notificationItem, firstItem);

    // Limit the number of notifications shown (keep only 5)
    const items = notificationList.querySelectorAll('.notification-item');
    if (items.length > 5) {
        for (let i = 5; i < items.length; i++) {
            items[i].remove();
        }
    }
}

function showToast(notification) {
    // Check if we have Bootstrap toast container
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        // Create toast container if it doesn't exist
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    let notificationTitle;
    switch(notification.notification_type) {
        case 'like':
            notificationTitle = 'Ai đó thích bài viết của bạn';
            break;
        case 'comment':
            notificationTitle = 'Bình luận mới';
            break;
        case 'follow':
            notificationTitle = 'Người theo dõi mới';
            break;
        case 'mention':
            notificationTitle = 'Bạn được nhắc đến';
            break;
        case 'message':
            notificationTitle = 'Tin nhắn mới';
            break;
        default:
            notificationTitle = 'Thông báo mới';
    }

    let notificationText;
    switch(notification.notification_type) {
        case 'like':
            notificationText = `${notification.sender_username} đã thích bài viết của bạn`;
            break;
        case 'comment':
            notificationText = `${notification.sender_username} đã bình luận về bài viết của bạn`;
            break;
        case 'follow':
            notificationText = `${notification.sender_username} đã theo dõi bạn`;
            break;
        case 'mention':
            notificationText = `${notification.sender_username} đã nhắc đến bạn trong bài viết`;
            break;
        case 'message':
            notificationText = `${notification.sender_username} đã gửi tin nhắn cho bạn`;
            break;
        default:
            notificationText = notification.text || 'Bạn có thông báo mới';
    }

    toastEl.innerHTML = `
        <div class="toast-header">
            <img src="${notification.sender_avatar}" class="rounded me-2" width="20" height="20" alt="${notification.sender_username}">
            <strong class="me-auto">${notificationTitle}</strong>
            <small>vừa mới</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${notificationText}
        </div>
    `;

    toastContainer.appendChild(toastEl);

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl);
    toast.show();

    // Remove the toast after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

function setupNotificationInteractions() {
    // Mark all notifications as read
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
                    // Update UI
                    document.querySelectorAll('.notification-item').forEach(item => {
                        item.classList.remove('bg-light');
                    });
                    updateNotificationCount(0);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    // Mark individual notification as read on click
    document.addEventListener('click', function(e) {
        const notificationItem = e.target.closest('.notification-item');
        if (notificationItem) {
            const notificationId = notificationItem.dataset.id;
            
            fetch(`/notifications/mark-as-read/${notificationId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI
                    notificationItem.classList.remove('bg-light');
                    
                    // Update count
                    const currentCount = parseInt(document.getElementById('notification-count').textContent);
                    if (currentCount > 0) {
                        updateNotificationCount(currentCount - 1);
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        }
    });
}

// Helper function to get CSRF token
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