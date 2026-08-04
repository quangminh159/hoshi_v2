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

    function updateSubtitleCount() {
        const subtitle = document.querySelector('.chat-list-subtitle');
        if (!subtitle) return;
        const count = document.querySelectorAll('#conversationList .conversation-wrapper').length;
        subtitle.textContent = count
            ? `${count} cuộc trò chuyện`
            : 'Chưa có cuộc trò chuyện nào';
    }

    function ensureSearchBox() {
        if (document.getElementById('conversationSearch')) return;
        const shell = document.querySelector('.chat-shell');
        const list = document.getElementById('conversationList');
        if (!shell || !list) return;
        const box = document.createElement('div');
        box.className = 'chat-search-box';
        box.innerHTML = `
            <i class="fas fa-search"></i>
            <input type="search" id="conversationSearch" placeholder="Tìm kiếm cuộc trò chuyện..." autocomplete="off">
        `;
        shell.insertBefore(box, list);
        box.querySelector('input')?.addEventListener('input', function () {
            const term = this.value.toLowerCase().trim();
            document.querySelectorAll('#conversationList .conversation-wrapper').forEach((wrap) => {
                const username = (wrap.dataset.username || '').toLowerCase();
                const preview = (wrap.querySelector('.conversation-last-message')?.textContent || '').toLowerCase();
                wrap.style.display = (!term || username.includes(term) || preview.includes(term)) ? '' : 'none';
            });
        });
    }

    function createConversationWrapper(conversationId, message, otherUser, currentUserId) {
        const username = otherUser?.username || message.sender_username || 'user';
        const avatar = otherUser?.avatar_url || '/static/img/default-avatar.png';
        const isMine = Number(message.sender_id) === Number(currentUserId);
        // other_user là người kia trong chat; nếu thiếu payload thì lấy từ sender khi tin đến
        const displayName = otherUser?.username
            || (isMine ? 'Cuộc trò chuyện' : (message.sender_username || 'user'));
        const displayAvatar = otherUser?.avatar_url
            || (!isMine && message.sender_avatar ? message.sender_avatar : avatar);

        const wrapper = document.createElement('div');
        wrapper.className = 'conversation-wrapper';
        wrapper.id = `conversation-${conversationId}`;
        wrapper.dataset.username = String(displayName).toLowerCase();
        wrapper.dataset.unread = '0';
        wrapper.innerHTML = `
            <a href="/chat/conversations/${conversationId}/" class="conversation-item">
              <div class="conversation-avatar">
                <img src="${escapeHtml(displayAvatar)}" alt="${escapeHtml(displayName)}">
              </div>
              <div class="conversation-info">
                <div class="conversation-name">
                  <span>${escapeHtml(displayName)}</span>
                  <span class="conversation-time">${formatTime(message.created_at)}</span>
                </div>
                <div class="conversation-last-message">${formatPreview(message, currentUserId)}</div>
              </div>
            </a>
            <button class="delete-conversation"
                    onclick="deleteConversation(${conversationId}, event)"
                    title="Xóa cuộc trò chuyện">
              <i class="fas fa-trash-alt"></i>
            </button>
        `;
        return wrapper;
    }

    function updateConversationList(conversationId, message, currentUserId, otherUser) {
        const list = document.getElementById('conversationList');
        if (!list) return;

        let wrapper = document.getElementById(`conversation-${conversationId}`)
            || list.querySelector(`.conversation-wrapper a[href*="/conversations/${conversationId}/"]`)?.closest('.conversation-wrapper');

        if (!wrapper) {
            list.querySelector('.no-conversations')?.remove();
            ensureSearchBox();
            wrapper = createConversationWrapper(conversationId, message, otherUser, currentUserId);
            list.insertBefore(wrapper, list.firstChild);
            updateSubtitleCount();

            const isMine = Number(message.sender_id) === Number(currentUserId);
            if (!isMine) {
                setUnread(wrapper, 1);
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

        const first = list.querySelector('.conversation-wrapper');
        if (first !== wrapper) {
            list.insertBefore(wrapper, first);
        }

        // Badge tổng do notifications.js refresh; ở đây chỉ cập nhật chấm từng hội thoại
        const isMine = Number(message.sender_id) === Number(currentUserId);
        if (!isMine) {
            const prev = parseInt(wrapper.dataset.unread || '0', 10) || 0;
            setUnread(wrapper, prev + 1);
        }
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
            // Dùng inbox WS toàn cục từ notifications.js
            window.addEventListener('hoshi:inbox-message', (event) => {
                const detail = event.detail || {};
                if (!detail.conversation_id || !detail.message) return;
                updateConversationList(
                    detail.conversation_id,
                    detail.message,
                    currentUserId,
                    detail.other_user || null
                );
            });
        }

        window.updateConversationList = function (conversationId, message, otherUser) {
            updateConversationList(conversationId, message, currentUserId, otherUser || null);
        };
    });
})();
