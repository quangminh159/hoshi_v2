// Notifications Websocket Connection
let wsReconnectAttempts = 0;
const WS_MAX_RECONNECT = 3;
let wsDisabled = false;

document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('user-authenticated') && !wsDisabled) {
        connectWebSocket();
        connectChatInboxSocket();
    }

    setupNotificationInteractions();

    // Đồng bộ badge tin nhắn khi vào/thoát trang chat
    if (document.body.classList.contains('user-authenticated')) {
        refreshChatUnreadCount();
        if (document.body.classList.contains('chat-detail-layout')
            || document.body.classList.contains('chat-layout')) {
            // Sau khi mở chat (đã mark read server-side), cập nhật lại badge
            setTimeout(refreshChatUnreadCount, 400);
        }
    }
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
            if (data && data.type === 'post_engagement') {
                handlePostEngagement(data);
                return;
            }
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

/** Inbox chat toàn cục — toast + badge khi đang ngoài trang tin nhắn. */
let chatInboxReconnectAttempts = 0;
function connectChatInboxSocket() {
    const userId = document.body.dataset.userId;
    if (!userId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    let socket;
    try {
        socket = new WebSocket(`${protocol}${window.location.host}/ws/chat/inbox/`);
    } catch (err) {
        console.error('Chat inbox WS error:', err);
        return;
    }

    socket.addEventListener('open', () => {
        chatInboxReconnectAttempts = 0;
    });

    socket.addEventListener('message', (event) => {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (_) {
            return;
        }
        if (data.signal || (data.type && String(data.type).startsWith('call_'))) {
            window.HoshiCall?.handleSignal(data);
            return;
        }
        if (data.type === 'message_request_accepted') {
            window.dispatchEvent(new CustomEvent('hoshi:message-request-accepted', {
                detail: {
                    conversation_id: data.conversation_id,
                    accepted_by: data.accepted_by || null,
                    other_user: data.other_user || null,
                    conversation: data.conversation || null,
                },
            }));
            return;
        }
        if (data.type === 'messages_read') {
            window.dispatchEvent(new CustomEvent('hoshi:messages-read', {
                detail: {
                    conversation_id: data.conversation_id,
                    message_ids: data.message_ids || [],
                    read_by: data.read_by,
                },
            }));
            return;
        }
        if (data.type === 'user_status') {
            window.dispatchEvent(new CustomEvent('hoshi:user-status', {
                detail: {
                    user_id: data.user_id,
                    status: data.status,
                    last_seen: data.last_seen || null,
                },
            }));
            return;
        }
        if (data.type !== 'inbox_message' || !data.conversation_id || !data.message) return;
        handleChatInboxMessage(data);
    });

    socket.addEventListener('close', () => {
        chatInboxReconnectAttempts += 1;
        const delay = Math.min(15000, 3000 * chatInboxReconnectAttempts);
        setTimeout(connectChatInboxSocket, delay);
    });
}

function buildMessageToastPreview(message) {
    if (message.content) {
        const text = String(message.content).trim();
        return text.length > 80 ? `${text.slice(0, 80)}…` : text;
    }
    if (message.attachment_type === 'image' || message.image) return 'Đã gửi một ảnh';
    if (message.attachment_type === 'video' || message.video) return 'Đã gửi một video';
    if (message.attachment_type === 'audio' || message.audio) return 'Đã gửi tin nhắn thoại';
    if (message.attachment_type === 'document' || message.document) return 'Đã gửi một tài liệu';
    if (message.shared_post) return 'Đã chia sẻ một bài viết';
    return 'đã gửi tin nhắn cho bạn';
}

function handleChatInboxMessage(data) {
    const message = data.message || {};
    const conversationId = data.conversation_id;
    const currentUserId = document.body.dataset.userId;
    const isMine = Number(message.sender_id) === Number(currentUserId);

    // Cập nhật danh sách hội thoại nếu đang mở trang tin nhắn
    window.dispatchEvent(new CustomEvent('hoshi:inbox-message', {
        detail: {
            conversation_id: conversationId,
            message,
            other_user: data.other_user || null,
            conversation: data.conversation || null,
        },
    }));

    if (isMine) return;

    refreshChatUnreadCount();

    // Đang trong khung chat / list tin nhắn → không toast
    if (isOnChatPage()) return;

    // Hội thoại đã tắt thông báo → không toast
    if (data.is_muted || data.conversation?.is_muted) return;

    // Tin hệ thống nhóm: toast nội dung nguyên văn
    if (message.is_system) {
        const groupTitle = data.conversation?.is_group ? data.conversation.title : null;
        showToast({
            notification_type: 'message',
            sender_username: groupTitle || 'Nhóm chat',
            sender_avatar: data.conversation?.avatar_url || '/static/img/default-avatar.png',
            text: message.content || 'Cập nhật nhóm',
            conversation_id: conversationId,
            link: `/chat/conversations/${conversationId}/`,
        });
        return;
    }

    const groupTitle = data.conversation?.is_group ? data.conversation.title : null;
    const username = message.sender_username || data.other_user?.username || 'Ai đó';
    const preview = buildMessageToastPreview(message);
    const bodyText = groupTitle
        ? (preview === 'đã gửi tin nhắn cho bạn'
            ? `${username} đã gửi tin trong ${groupTitle}`
            : `${groupTitle} · ${username}: ${preview}`)
        : (preview === 'đã gửi tin nhắn cho bạn'
            ? `${username} đã gửi tin nhắn cho bạn`
            : `${username}: ${preview}`);

    showToast({
        notification_type: 'message',
        sender_username: groupTitle || username,
        sender_avatar: data.conversation?.avatar_url || message.sender_avatar || data.other_user?.avatar_url || '/static/img/default-avatar.png',
        text: bodyText,
        conversation_id: conversationId,
        link: `/chat/conversations/${conversationId}/`,
    });
}

function applyLiveLikeCount(postId, count) {
    if (typeof window.setPostLikeCount === 'function') {
        window.setPostLikeCount(postId, count);
        return;
    }
    const n = Math.max(0, Number(count) || 0);
    document.querySelectorAll(`.likes-count[data-post-id="${postId}"]`).forEach((el) => {
        el.textContent = String(n);
    });
    document.querySelectorAll(`.likes-count-text[data-post-id="${postId}"], .likes-count-text`).forEach((el) => {
        if (el.dataset.postId && String(el.dataset.postId) !== String(postId)) return;
        el.textContent = `${n} lượt thích`;
    });
    document.querySelectorAll(`.likes-count-display a[data-post-id="${postId}"]`).forEach((el) => {
        const textEl = el.querySelector('.likes-count-text');
        if (textEl) textEl.textContent = `${n} lượt thích`;
        else el.textContent = `${n} lượt thích`;
    });
}

function applyLiveCommentCount(postId, count) {
    if (typeof window.setPostCommentCount === 'function') {
        window.setPostCommentCount(postId, count);
        return;
    }
    const n = Math.max(0, Number(count) || 0);
    document.querySelectorAll(
        `.comments-count[data-post-id="${postId}"], `
        + `.post-comment-count[data-post-id="${postId}"], `
        + `#post-comment-count, #post-comment-count-actions`
    ).forEach((el) => {
        if (el.dataset.postId && String(el.dataset.postId) !== String(postId)) return;
        if ((el.id === 'post-comment-count' || el.id === 'post-comment-count-actions')) {
            const pagePost = document.querySelector('.like-button[data-post-id]');
            if (pagePost && String(pagePost.getAttribute('data-post-id')) !== String(postId)) return;
        }
        el.textContent = String(n);
    });
}

/** Realtime: người khác like/cmt → cập nhật số trên bài đang hiện (không cần reload). */
function applyLiveCommentLikeCount(commentId, likesCount) {
    const n = Number(likesCount) || 0;
    const text = n > 0 ? String(n) : '';
    document.querySelectorAll(`.comment-likes-count[data-comment-id="${commentId}"]`).forEach((el) => {
        el.textContent = text;
    });
}

function applyLiveCommentRepliesCount(commentId, repliesCount) {
    const n = Number(repliesCount) || 0;
    const text = n > 0 ? String(n) : '';
    let updated = false;
    document.querySelectorAll(`.comment-replies-count[data-comment-id="${commentId}"]`).forEach((el) => {
        el.textContent = text;
        updated = true;
    });
    if (!updated && n > 0) {
        const replyBtn = document.querySelector(
            `#comment-${commentId} .reply-button[data-comment-id="${commentId}"], `
            + `.root-comment[data-comment-id="${commentId}"] .reply-button[data-comment-id="${commentId}"]`
        );
        if (replyBtn && !replyBtn.querySelector('.comment-replies-count')) {
            replyBtn.insertAdjacentHTML(
                'beforeend',
                `<span class="comment-replies-count" data-comment-id="${commentId}">${text}</span>`
            );
        }
    }
}

function applyLiveNewComment(data) {
    const comment = data && data.comment;
    if (!comment || comment.id == null) return;

    const postId = data.post_id != null ? data.post_id : comment.post_id;
    if (postId == null) return;

    if (
        document.getElementById(`comment-${comment.id}`)
        || document.querySelector(`[data-comment-id="${comment.id}"]`)
    ) {
        return;
    }

    const myId = document.body && document.body.dataset.userId;
    if (myId && String(comment.author_id) === String(myId)) {
        comment.can_delete = true;
        comment.can_edit = true;
    }

    const parentId = (comment.parent && comment.parent.id)
        || comment.parent_id
        || data.parent_comment_id
        || null;
    const isReply = !!parentId;

    // Feed (infinite scroll)
    if (typeof window.appendCommentToFeed === 'function' && document.getElementById(`post-${postId}`)) {
        window.appendCommentToFeed(comment, postId, isReply, parentId);
        return;
    }

    // Trang chi tiết bài
    const onDetail = !!document.getElementById('post-detail-comments-list')
        || !!document.querySelector(`.post-detail[data-post-id="${postId}"], #post-${postId}`);
    if (onDetail && typeof window.addCommentToDOM === 'function') {
        window.addCommentToDOM(comment, postId, parentId);
    }
}

function handlePostEngagement(data) {
    if (!data) return;
    const postId = data.post_id;
    const commentId = data.comment_id;

    // Chèn bình luận mới trước, rồi ghi đè số đếm bằng giá trị tuyệt đối từ server
    if (data.action === 'comment_add' && data.comment) {
        applyLiveNewComment(data);
    }

    if (postId != null) {
        const visible = document.querySelector(
            `#post-${postId}, .likes-count[data-post-id="${postId}"], `
            + `.comments-count[data-post-id="${postId}"], .like-button[data-post-id="${postId}"], `
            + `#post-detail-comments-list, .post-comment-count[data-post-id="${postId}"]`
        );
        if (visible) {
            if (typeof data.likes_count === 'number') {
                applyLiveLikeCount(postId, data.likes_count);
            }
            if (typeof data.comments_count === 'number') {
                applyLiveCommentCount(postId, data.comments_count);
            }
        }
    }

    if (commentId != null && typeof data.comment_likes_count === 'number') {
        if (document.querySelector(`#comment-${commentId}, .comment-likes-count[data-comment-id="${commentId}"]`)) {
            applyLiveCommentLikeCount(commentId, data.comment_likes_count);
        }
    }

    const parentId = data.parent_comment_id;
    if (parentId != null && typeof data.replies_count === 'number') {
        if (document.querySelector(`#comment-${parentId}, .comment-replies-count[data-comment-id="${parentId}"]`)) {
            applyLiveCommentRepliesCount(parentId, data.replies_count);
        }
    }
}

function handleNotification(data) {
    if (data && data.type === 'post_engagement') {
        handlePostEngagement(data);
        return;
    }
    const notification = data.notification;
    const isMessage = notification && notification.notification_type === 'message';

    // Tin nhắn không hiện trong feed Thông báo — chỉ cập nhật badge chat
    if (isMessage) {
        const activeId = getActiveConversationId();
        const notifConv = notification.conversation_id != null
            ? String(notification.conversation_id)
            : null;
        if (!(isOnChatPage() && activeId && notifConv && activeId === notifConv)) {
            refreshChatUnreadCount();
        }
        return;
    }

    if (typeof data.unread_count !== 'undefined') {
        updateNotificationCount(data.unread_count);
    }

    if (notification && Object.keys(notification).length > 0) {
        addNotificationToList(notification);
        // Đang ở trang thông báo thì đã thấy item mới — không cần toast
        const onNotificationsPage = !!document.getElementById('notifications-list');
        if (!onNotificationsPage && !shouldSuppressToast(notification)) {
            showToast(notification);
        }
    }
}

function updateChatUnreadCount(count) {
    const n = Math.max(0, parseInt(count, 10) || 0);
    const label = n > 99 ? '99+' : String(n);

    const badge = document.getElementById('chat-unread-count');
    if (badge) {
        badge.innerHTML = `${label}<span class="visually-hidden">tin nhắn chưa đọc</span>`;
        badge.style.display = n > 0 ? '' : 'none';
    }

    const dot = document.getElementById('chat-unread-dot');
    if (dot) {
        dot.classList.toggle('d-none', n <= 0);
    }

    const mobileLabel = document.getElementById('chat-unread-count-mobile');
    if (mobileLabel) {
        mobileLabel.textContent = n > 0 ? label : '';
    }
}

function refreshChatUnreadCount() {
    if (!document.body.classList.contains('user-authenticated')) return;
    fetch('/chat/api/unread-total/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
    })
        .then((r) => r.json())
        .then((data) => {
            if (data && data.ok) updateChatUnreadCount(data.unread_count);
        })
        .catch(() => {});
}

window.refreshChatUnreadCount = refreshChatUnreadCount;
window.updateChatUnreadCount = updateChatUnreadCount;

function getActiveConversationId() {
    const fromPage = document.querySelector('.chat-page[data-conversation-id]');
    if (fromPage && fromPage.dataset.conversationId) {
        return String(fromPage.dataset.conversationId);
    }

    const fromBody = document.body.dataset.conversationId;
    if (fromBody) return String(fromBody);

    const match = window.location.pathname.match(/\/chat\/conversations\/(\d+)\/?/);
    return match ? match[1] : null;
}

function isOnChatPage() {
    return document.body.classList.contains('chat-layout')
        || document.body.classList.contains('chat-detail-layout')
        || window.location.pathname.startsWith('/chat/');
}

/** Không hiện toast tin nhắn khi đang ở trang chat (đã xem realtime). */
function shouldSuppressToast(notification) {
    if (!notification || notification.notification_type !== 'message') {
        return false;
    }
    if (isOnChatPage()) {
        return true;
    }
    const activeId = getActiveConversationId();
    const notifId = notification.conversation_id != null
        ? String(notification.conversation_id)
        : null;
    return Boolean(activeId && notifId && activeId === notifId);
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
    if (notification.notification_type === 'follow_request' && notification.sender_username) {
        return `/users/${notification.sender_username}/`;
    }
    if (notification.notification_type === 'follow_accepted' && notification.sender_username) {
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
        case 'follow_request':
            return 'Yêu cầu theo dõi';
        case 'follow_accepted':
            return 'Đã chấp nhận theo dõi';
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
    if (!notification || !notification.id) return;

    addNotificationToDropdown(notification);
    addNotificationToPage(notification);
}

function addNotificationToDropdown(notification) {
    const dropdownList = document.querySelector('.notification-dropdown .notification-list');
    if (!dropdownList) return;

    const emptyState = dropdownList.querySelector('.text-center.text-muted');
    if (emptyState) {
        emptyState.remove();
    }

    if (dropdownList.querySelector(`[data-id="${notification.id}"]`)) return;

    const link = getNotificationLink(notification);
    const isFollowRequest = notification.notification_type === 'follow_request';
    const notificationItem = document.createElement(isFollowRequest ? 'div' : 'a');
    if (!isFollowRequest) {
        notificationItem.href = link;
        notificationItem.className = 'notification-item p-3 border-bottom bg-light text-decoration-none text-body d-block';
    } else {
        notificationItem.className = 'notification-item p-3 border-bottom bg-light';
        notificationItem.dataset.type = 'follow_request';
        notificationItem.dataset.username = notification.sender_username || '';
    }
    notificationItem.dataset.id = notification.id;
    notificationItem.dataset.link = link;

    const actionsHtml = isFollowRequest && typeof window.renderFollowRequestActions === 'function'
        ? window.renderFollowRequestActions(notification.sender_username || '')
        : (isFollowRequest
            ? `<div class="d-flex gap-2 follow-request-actions mt-2">
                <button type="button" class="btn btn-sm btn-primary accept-follow-request" data-username="${notification.sender_username || ''}">Xác nhận</button>
                <button type="button" class="btn btn-sm btn-outline-secondary reject-follow-request" data-username="${notification.sender_username || ''}">Từ chối</button>
               </div>`
            : '');

    notificationItem.innerHTML = `
        <div class="d-flex">
            <img src="${notification.sender_avatar || '/static/img/default-avatar.png'}" class="rounded-circle me-2" width="40" height="40" alt="${notification.sender_username || 'User'}">
            <div class="flex-grow-1">
                <p class="mb-1">${getNotificationText(notification)}</p>
                <small class="text-muted">vừa mới</small>
                ${actionsHtml}
            </div>
        </div>
    `;

    dropdownList.insertBefore(notificationItem, dropdownList.firstChild);

    const items = dropdownList.querySelectorAll('.notification-item');
    if (items.length > 5) {
        for (let i = 5; i < items.length; i++) {
            items[i].remove();
        }
    }
}

function escapeHtmlNotif(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/** Thêm thông báo realtime vào trang /notifications/ (cuộn vô hạn). */
function addNotificationToPage(notification) {
    const pageList = document.getElementById('notifications-list');
    if (!pageList) return;

    if (pageList.querySelector(`[data-id="${notification.id}"]`)) return;

    document.getElementById('notifications-empty')?.remove();
    document.getElementById('notifications-end')?.classList.add('d-none');

    const link = getNotificationLink(notification);
    const username = escapeHtmlNotif(notification.sender_username || '');
    const avatar = escapeHtmlNotif(notification.sender_avatar || '/static/img/default-avatar.png');
    const text = escapeHtmlNotif(getNotificationText(notification));
    const isFollowRequest = notification.notification_type === 'follow_request';

    let el;
    if (isFollowRequest) {
        el = document.createElement('div');
        el.className = 'list-group-item bg-light new-notification';
        el.dataset.type = 'follow_request';
        el.dataset.username = notification.sender_username || '';
        el.innerHTML = `
            <div class="d-flex w-100 justify-content-between align-items-center gap-2 flex-wrap">
                <div class="d-flex align-items-center">
                    <a href="${escapeHtmlNotif(link)}" class="text-decoration-none text-dark">
                        <img src="${avatar}" class="rounded-circle me-2" width="40" height="40" alt="${username}">
                    </a>
                    <div>
                        <a href="${escapeHtmlNotif(link)}" class="text-decoration-none text-dark">
                            <strong>${username}</strong>
                        </a>
                        ${text}
                        <div><small class="text-muted">vừa mới</small></div>
                    </div>
                </div>
                <div class="d-flex gap-2 follow-request-actions">
                    <button type="button" class="btn btn-sm btn-primary accept-follow-request" data-username="${username}">Xác nhận</button>
                    <button type="button" class="btn btn-sm btn-outline-secondary reject-follow-request" data-username="${username}">Từ chối</button>
                </div>
            </div>
        `;
    } else {
        el = document.createElement('a');
        el.href = link;
        el.className = 'list-group-item list-group-item-action text-decoration-none text-dark bg-light new-notification';
        el.innerHTML = `
            <div class="d-flex w-100 justify-content-between gap-2">
                <div class="d-flex align-items-start">
                    <img src="${avatar}" class="rounded-circle me-2" width="40" height="40" alt="${username}">
                    <div>
                        <strong>${username}</strong>
                        ${text}
                    </div>
                </div>
                <small class="text-muted text-nowrap">vừa mới</small>
            </div>
        `;
    }

    el.id = `notification-${notification.id}`;
    el.dataset.id = notification.id;

    pageList.insertBefore(el, pageList.firstChild);

    if (typeof window.notificationsInfiniteRegister === 'function') {
        window.notificationsInfiniteRegister(notification.id);
    }

    // Hiện nút đánh dấu tất cả nếu chưa có
    const header = document.querySelector('.notifications-page .d-flex.justify-content-between');
    if (header && !header.querySelector('.mark-all-read')) {
        const markLink = document.createElement('a');
        markLink.href = '/notifications/mark-all-as-read/';
        markLink.className = 'text-decoration-none text-primary small mark-all-read';
        markLink.textContent = 'Đánh dấu tất cả đã đọc';
        header.appendChild(markLink);
    }
}

function showToast(notification) {
    let toastContainer = document.querySelector('.toast-container');

    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed end-0 p-3 hoshi-toast-container';
        document.body.appendChild(toastContainer);
    }

    const toastEl = document.createElement('div');
    const type = notification.notification_type || 'default';
    toastEl.className = `toast hoshi-toast hoshi-toast--${type}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    const link = getNotificationLink(notification);
    const notificationTitle = getNotificationTitle(notification);
    const senderName = String(notification.sender_username || '').trim();
    let bodyText = String(getNotificationText(notification) || '').trim();

    // Bỏ prefix "username: " nếu body đã gồm tên (toast tin nhắn)
    if (senderName) {
        const prefix = `${senderName}:`;
        if (bodyText.toLowerCase().startsWith(prefix.toLowerCase())) {
            bodyText = bodyText.slice(prefix.length).trim();
        }
    }

    const avatar = escapeHtmlNotif(notification.sender_avatar || '/static/img/default-avatar.png');
    const safeTitle = escapeHtmlNotif(notificationTitle);
    const safeName = escapeHtmlNotif(senderName);
    const safeBody = escapeHtmlNotif(bodyText);
    const safeLink = escapeHtmlNotif(link);

    const displayName = safeName || safeTitle;
    const subtitle = safeName ? safeTitle : '';

    toastEl.innerHTML = `
        <div class="hoshi-toast__inner">
            <img src="${avatar}" class="hoshi-toast__avatar" width="44" height="44" alt="">
            <div class="hoshi-toast__body">
                <div class="hoshi-toast__row">
                    <span class="hoshi-toast__name">${displayName}</span>
                    <span class="hoshi-toast__time">vừa mới</span>
                </div>
                ${subtitle ? `<div class="hoshi-toast__label">${subtitle}</div>` : ''}
                ${safeBody ? `<p class="hoshi-toast__text">${safeBody}</p>` : ''}
            </div>
            <button type="button" class="hoshi-toast__close" data-bs-dismiss="toast" aria-label="Đóng">
                <i class="fas fa-times" aria-hidden="true"></i>
            </button>
        </div>
    `;

    if (link && link !== '#') {
        toastEl.style.cursor = 'pointer';
        toastEl.addEventListener('click', (e) => {
            if (e.target.closest('.hoshi-toast__close')) return;
            window.location.href = link;
        });
        toastEl.setAttribute('data-href', safeLink);
    }

    toastContainer.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl, { delay: 5200, autohide: true });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', function () {
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
    document.addEventListener('click', function(e) {
        const markAllReadBtn = e.target.closest('.mark-all-read');
        if (markAllReadBtn) {
            e.preventDefault();
            const url = markAllReadBtn.getAttribute('href') || '/notifications/mark-all-as-read/';

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
                .then((response) => {
                    if (!response.ok) throw new Error('mark all failed');
                    return response.json();
                })
                .then((data) => {
                    if (!data.success) return;
                    document.querySelectorAll(
                        '.notification-item, .list-group-item[data-id], #notifications-list .list-group-item'
                    ).forEach((item) => {
                        item.classList.remove('bg-light');
                    });
                    updateNotificationCount(0);
                })
                .catch((error) => console.error('Error:', error));
            return;
        }

        const notificationItem = e.target.closest('.notification-item[data-id], .list-group-item[data-id]');
        if (!notificationItem) return;
        if (e.target.closest('.accept-follow-request, .reject-follow-request')) return;

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
