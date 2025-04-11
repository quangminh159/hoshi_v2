/**
 * Chat Detail JavaScript - Xử lý giao diện chat
 * 
 * Phần code này đã được chuyển vào template conversation_detail.html
 */

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo WebSocket
    const conversationId = document.querySelector('[data-conversation-id]').dataset.conversationId;
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const chatSocket = new WebSocket(
        `${wsScheme}://${window.location.host}/ws/chat/${conversationId}/`
    );

    // Xử lý khi nhận tin nhắn mới
    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        if (data.type === 'chat_message') {
            // Thêm tin nhắn mới vào giao diện
            appendMessage(data.message);
        } else if (data.type === 'typing') {
            // Hiển thị trạng thái đang nhập
            handleTypingStatus(data);
        } else if (data.type === 'read_receipt') {
            // Cập nhật trạng thái đã đọc
            updateMessageStatus(data.message_id);
        }
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
        // Thử kết nối lại sau 3 giây
        setTimeout(() => {
            window.location.reload();
        }, 3000);
    };

    // Xử lý gửi tin nhắn
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');

    messageInput.addEventListener('input', function() {
        if (this.value.trim()) {
            sendButton.style.display = 'flex';
        } else {
            sendButton.style.display = 'none';
        }
    });

    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        
        if (message) {
            chatSocket.send(JSON.stringify({
                'type': 'message',
                'message': message
            }));
            messageInput.value = '';
            sendButton.style.display = 'none';
        }
    });

    // Xử lý trạng thái đang nhập
    let typingTimeout;
    messageInput.addEventListener('input', function() {
        if (!typingTimeout) {
            chatSocket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': true
            }));
        }
        
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
            chatSocket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': false
            }));
            typingTimeout = null;
        }, 1000);
    });

    // Cuộn đến tin nhắn cuối cùng khi tải trang
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Thêm tin nhắn mới vào giao diện
    function appendMessage(message) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `message mb-3 ${message.sender_id === currentUserId ? 'sent' : 'received'}`;
        
        messageContainer.innerHTML = `
            <div class="d-flex ${message.sender_id === currentUserId ? 'justify-content-end' : ''}">
                ${message.sender_id !== currentUserId ? `
                    <div class="me-2">
                        <img src="${message.sender_avatar || '/static/img/default-avatar.png'}" 
                             alt="${message.sender_username}" 
                             class="rounded-circle"
                             width="32" 
                             height="32"
                             style="object-fit: cover;">
                    </div>
                ` : ''}
                <div class="message-bubble ${message.sender_id === currentUserId ? 'sent-bubble' : 'received-bubble'}" style="max-width: 75%;">
                    ${message.content}
                    <div class="message-time" style="font-size: 11px; color: #8e8e8e; margin-top: 4px; text-align: right;">
                        ${new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        ${message.sender_id === currentUserId ? `
                            <i class="fas fa-check ms-1" style="font-size: 10px;"></i>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageContainer);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Xử lý trạng thái đang nhập
    function handleTypingStatus(data) {
        const typingIndicator = document.getElementById('typing-indicator');
        if (data.is_typing && data.user_id !== currentUserId) {
            typingIndicator.classList.remove('d-none');
        } else {
            typingIndicator.classList.add('d-none');
        }
    }
    
    // Xử lý attachment preview khi click vào ảnh
    document.querySelectorAll('.img-attachment').forEach(img => {
        img.addEventListener('click', function() {
            const modal = document.createElement('div');
            modal.className = 'modal fade image-preview-modal';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body p-0">
                            <button type="button" class="btn-close position-absolute top-0 end-0 m-2" data-bs-dismiss="modal" aria-label="Close"></button>
                            <img src="${this.src}" class="img-fluid" alt="Image Preview">
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            modal.addEventListener('hidden.bs.modal', function() {
                document.body.removeChild(modal);
            });
        });
    });
    
    // Cập nhật trạng thái message khi WebSocket nhận được thông báo read_receipt
    function updateMessageStatus(messageId) {
        const message = document.querySelector(`.message-item[data-message-id="${messageId}"]`);
        if (message) {
            const statusEl = message.querySelector('.message-status');
            if (statusEl) {
                statusEl.innerHTML = '<i class="bi bi-check-all text-primary"></i>';
            }
        }
    }
    
    // Xử lý nút xóa tin nhắn
    document.querySelectorAll('.delete-message-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const messageId = this.closest('.message-item').dataset.messageId;
            if (confirm('Bạn có chắc chắn muốn xóa tin nhắn này không?')) {
                fetch(`/chat/api/messages/${messageId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    }
                })
                .then(response => {
                    if (response.ok) {
                        const messageBubble = this.closest('.message-bubble');
                        messageBubble.innerHTML = '<span class="message-deleted"><i class="bi bi-trash"></i> Tin nhắn đã bị xóa</span>';
                    }
                });
            }
        });
    });
    
    // Lấy CSRF token từ cookie
    function getCsrfToken() {
        const name = 'csrftoken';
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
}); 