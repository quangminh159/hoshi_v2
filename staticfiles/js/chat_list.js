/**
 * Chat List JavaScript - Xử lý danh sách cuộc trò chuyện
 */

document.addEventListener('DOMContentLoaded', function() {
    // Xử lý tìm kiếm cuộc trò chuyện
    const searchInput = document.getElementById('searchConversations');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const conversationItems = document.querySelectorAll('.conversation-item');
            
            conversationItems.forEach(item => {
                const conversationName = item.querySelector('.conversation-name').textContent.toLowerCase();
                const conversationPreview = item.querySelector('.conversation-preview').textContent.toLowerCase();
                
                if (conversationName.includes(searchTerm) || conversationPreview.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Lắng nghe sự kiện khi WebSocket nhận được tin nhắn mới để cập nhật UI
    function updateConversationList(conversationId, lastMessage) {
        // Tìm cuộc trò chuyện trong danh sách
        const conversationItem = document.querySelector(`.conversation-item[href$="${conversationId}/"]`);
        if (conversationItem) {
            // Cập nhật tin nhắn preview
            const previewEl = conversationItem.querySelector('.conversation-preview');
            if (previewEl) {
                // Kiểm tra nếu là tin nhắn từ người dùng hiện tại
                const isCurrentUser = lastMessage.senderId === currentUserId;
                previewEl.innerHTML = isCurrentUser ? 
                    `<span class="sender-preview">Bạn:</span> ${lastMessage.content}` : 
                    lastMessage.content;
            }
            
            // Cập nhật thời gian
            const timeEl = conversationItem.querySelector('.conversation-time');
            if (timeEl) {
                const date = new Date(lastMessage.timestamp);
                const hours = date.getHours().toString().padStart(2, '0');
                const minutes = date.getMinutes().toString().padStart(2, '0');
                timeEl.textContent = `${hours}:${minutes}`;
            }
            
            // Đưa cuộc trò chuyện lên đầu danh sách
            const parent = conversationItem.parentNode;
            parent.prepend(conversationItem);
            
            // Thêm class unread nếu không phải là tin nhắn của người dùng hiện tại
            if (!isCurrentUser && !window.location.href.includes(`/conversations/${conversationId}/`)) {
                conversationItem.classList.add('unread');
                
                // Cập nhật badge số tin nhắn chưa đọc
                let unreadBadge = conversationItem.querySelector('.unread-badge');
                if (!unreadBadge) {
                    unreadBadge = document.createElement('div');
                    unreadBadge.className = 'unread-badge';
                    conversationItem.querySelector('.conversation-meta').appendChild(unreadBadge);
                }
                
                // Lấy số tin nhắn chưa đọc hiện tại và tăng thêm 1
                const unreadCount = parseInt(unreadBadge.textContent || '0') + 1;
                unreadBadge.textContent = unreadCount;
            }
        }
    }
    
    // Hàm này sẽ được gọi từ WebSocket trong template
    window.updateConversationList = updateConversationList;
}); 