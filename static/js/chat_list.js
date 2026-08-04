/**
 * Danh sách cuộc trò chuyện — cập nhật realtime qua /ws/chat/inbox/
 */
(function () {
    'use strict';

    function escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatPreview(message, currentUserId) {
        const senderId = message.sender_id;
        const isMine = Number(senderId) === Number(currentUserId);
        const prefix = isMine ? '<span class="you-prefix">Bạn: </span>' : '';

        if (message.content) {
            const text = escapeHtml(String(message.content).slice(0, 45));
            return prefix + text;
        }
        if (message.attachment_type === 'image' || message.image) {
            return `${prefix}<i class="far fa-image"></i> Hình ảnh`;
        }
        if (message.attachment_type === 'video' || message.video) {
            return `${prefix}<i class="far fa-file-video"></i> Video`;
        }
        if (message.attachment_type === 'audio' || message.audio) {
            return `${prefix}<i class="fas fa-microphone"></i> Tin nhắn thoại`;
        }
        if (message.attachment_type === 'document' || message.document) {
            return `${prefix}<i class="far fa-file-alt"></i> Tài liệu`;
        }
        if (message.shared_post) {
            return `${prefix}<i class="fas fa-share"></i> Bài viết`;
        }
        return `${prefix}<em>Tin nhắn mới</em>`;
    }

    function formatTime(iso) {
        const date = iso ? new Date(iso) : new Date();
        if (Number.isNaN(date.getTime())) return '';
        return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    }

    function setUnread(wrapper, count) {
        const n = Math.max(0, parseInt(count, 10) || 0);
        wrapper.dataset.unread = String(n);
        wrapper.classList.toggle('has-unread', n > 0);

        const avatar = wrapper.querySelector('.conversation-avatar');
        let dot = wrapper.querySelector('.conversation-unread-dot');
        let badge = wrapper.querySelector('.conversation-unread-badge');
        const nameEl = wrapper.querySelector('.conversation-name > span:first-child');
        const previewEl = wrapper.querySelector('.conversation-last-message');

        if (n > 0) {
            if (nameEl) nameEl.classList.add('fw-bold');
            if (previewEl) previewEl.classList.add('fw-semibold', 'text-body');
            if (avatar && !dot) {
                dot = document.createElement('span');
                dot.className = 'conversation-unread-dot';
                dot.setAttribute('aria-hidden', 'true');
                avatar.appendChild(dot);
            }
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'conversation-unread-badge';
                const item = wrapper.querySelector('.conversation-item');
                if (item) item.appendChild(badge);
            }
            if (badge) badge.textContent = n > 99 ? '99+' : String(n);
        } else {
            if (nameEl) nameEl.classList.remove('fw-bold');
            if (previewEl) previewEl.classList.remove('fw-semibold', 'text-body');
            if (dot) dot.remove();
            if (badge) badge.remove();
        }
    }

    function updateConversationList(conversationId, message, currentUserId) {
        const list = document.getElementById('conversationList');
        if (!list) return;

        const wrapper = document.getElementById(`conversation-${conversationId}`)
            || list.querySelector(`.conversation-wrapper a[href*="/conversations/${conversationId}/"]`)?.closest('.conversation-wrapper');

        if (!wrapper) {
            // Cuộc trò chuyện mới chưa có trong DOM — reload nhẹ phần list
            if (typeof window.refreshChatUnreadCount === 'function') {
                window.refreshChatUnreadCount();
            }
            return;
        }

        const previewEl = wrapper.querySelector('.conversation-last-message');
        if (previewEl && !previewEl.querySelector('.text-danger')) {
            previewEl.innerHTML = formatPreview(message, currentUserId);
        }

        const timeEl = wrapper.querySelector('.conversation-time');
        if (timeEl) {
            timeEl.textContent = formatTime(message.created_at);
        }

        // Đưa lên đầu danh sách
        const first = list.querySelector('.conversation-wrapper');
        if (first !== wrapper) {
            list.insertBefore(wrapper, first);
        }

        const isMine = Number(message.sender_id) === Number(currentUserId);
        if (!isMine) {
            const prev = parseInt(wrapper.dataset.unread || '0', 10) || 0;
            setUnread(wrapper, prev + 1);
        }

        if (typeof window.refreshChatUnreadCount === 'function') {
            window.refreshChatUnreadCount();
        }
    }

    function connectInboxSocket(currentUserId) {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socket = new WebSocket(`${protocol}${window.location.host}/ws/chat/inbox/`);

        socket.addEventListener('message', (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (_) {
                return;
            }
            if (data.type !== 'inbox_message' || !data.conversation_id || !data.message) return;
            updateConversationList(data.conversation_id, data.message, currentUserId);
        });

        socket.addEventListener('close', () => {
            setTimeout(() => connectInboxSocket(currentUserId), 4000);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const searchInput = document.getElementById('conversationSearch')
            || document.getElementById('searchConversations');
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                const term = this.value.toLowerCase().trim();
                document.querySelectorAll('#conversationList .conversation-wrapper').forEach((wrap) => {
                    const username = (wrap.dataset.username || '').toLowerCase();
                    const preview = (wrap.querySelector('.conversation-last-message')?.textContent || '').toLowerCase();
                    wrap.style.display = (!term || username.includes(term) || preview.includes(term)) ? '' : 'none';
                });
            });
        }

        const currentUserId = document.body.dataset.userId;
        if (currentUserId && document.getElementById('conversationList')) {
            connectInboxSocket(currentUserId);
        }

        window.updateConversationList = function (conversationId, message) {
            updateConversationList(conversationId, message, currentUserId);
        };
    });
})();
