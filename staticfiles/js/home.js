// Load posts
function loadPosts(page = 1) {
    $.get(`/api/posts/?page=${page}`, function(data) {
        const postList = $('#post-list');
        if (page === 1) {
            postList.empty();
        }
        
        data.results.forEach(post => {
            const postElement = createPostElement(post);
            postList.append(postElement);
        });
        
        if (data.next) {
            // Add load more button if there are more posts
            const loadMoreBtn = $('<button>')
                .addClass('btn btn-outline-primary w-100 mt-3')
                .text('Tải thêm')
                .click(() => loadPosts(page + 1));
            postList.append(loadMoreBtn);
        }
    });
}

// Create post element
function createPostElement(post) {
    const postDiv = $('<div>').addClass('post');
    
    // Post header
    const header = $('<div>').addClass('post-header');
    const avatar = $('<img>')
        .addClass('avatar')
        .attr('src', post.author.avatar)
        .attr('alt', post.author.username);
    const authorLink = $('<a>')
        .attr('href', `/profile/${post.author.username}`)
        .text(post.author.username);
    const timestamp = $('<small>')
        .addClass('text-muted ms-2')
        .text(new Date(post.created_at).toLocaleString());
    header.append(avatar, authorLink, timestamp);
    
    // Post content
    const content = $('<div>')
        .addClass('post-content')
        .text(post.content);
    
    // Post media
    const media = $('<div>').addClass('post-media');
    if (post.media && post.media.length > 0) {
        post.media.forEach(mediaItem => {
            if (mediaItem.type === 'image') {
                const img = $('<img>')
                    .addClass('img-fluid')
                    .attr('src', mediaItem.url)
                    .attr('alt', 'Post image');
                media.append(img);
            }
        });
    }
    
    // Post actions
    const actions = $('<div>').addClass('post-actions');
    const likeBtn = $('<button>')
        .addClass('btn btn-sm btn-outline-primary')
        .html(`<i class="fas fa-heart"></i> ${post.likes_count}`);
    const commentBtn = $('<button>')
        .addClass('btn btn-sm btn-outline-secondary')
        .html(`<i class="fas fa-comment"></i> ${post.comments_count}`);
    actions.append(likeBtn, commentBtn);
    
    // Add all elements to post
    postDiv.append(header, content, media, actions);
    return postDiv;
}

// Load notifications
function loadNotifications() {
    $.get('/api/notifications/', function(data) {
        const notificationsDiv = $('#notifications');
        notificationsDiv.empty();
        
        if (data.results.length === 0) {
            notificationsDiv.append('<p class="text-muted">Không có thông báo mới</p>');
            return;
        }
        
        data.results.forEach(notification => {
            const notificationElement = createNotificationElement(notification);
            notificationsDiv.append(notificationElement);
        });
    });
}

// Create notification element
function createNotificationElement(notification) {
    const div = $('<div>')
        .addClass('notification')
        .addClass(notification.is_read ? '' : 'unread')
        .attr('data-id', notification.id);
    
    const content = $('<div>').addClass('notification-content');
    const icon = $('<i>').addClass('fas');
    
    // Set icon based on notification type
    switch (notification.notification_type) {
        case 'like':
            icon.addClass('fa-heart text-danger');
            break;
        case 'comment':
            icon.addClass('fa-comment text-primary');
            break;
        case 'follow':
            icon.addClass('fa-user-plus text-success');
            break;
        case 'mention':
            icon.addClass('fa-at text-info');
            break;
        case 'message':
            icon.addClass('fa-envelope text-warning');
            break;
    }
    
    content.append(icon, ' ', notification.text);
    const time = $('<small>')
        .addClass('text-muted d-block')
        .text(new Date(notification.created_at).toLocaleString());
    
    div.append(content, time);
    
    // Mark as read when clicked
    div.click(function() {
        if (!notification.is_read) {
            $.post(`/api/notifications/${notification.id}/mark-read/`, function() {
                div.removeClass('unread');
                loadUnreadNotificationsCount();
            });
        }
    });
    
    return div;
}

// Load friend suggestions
function loadFriendSuggestions() {
    $.get('/api/accounts/suggestions/', function(data) {
        const suggestionsDiv = $('#friend-suggestions');
        suggestionsDiv.empty();
        
        if (data.length === 0) {
            suggestionsDiv.append('<p class="text-muted">Không có gợi ý nào</p>');
            return;
        }
        
        data.forEach(user => {
            const userElement = createUserElement(user);
            suggestionsDiv.append(userElement);
        });
    });
}

// Create user element for suggestions
function createUserElement(user) {
    const div = $('<div>').addClass('d-flex align-items-center mb-2');
    
    const avatar = $('<img>')
        .addClass('avatar me-2')
        .attr('src', user.avatar)
        .attr('alt', user.username);
    
    const info = $('<div>').addClass('flex-grow-1');
    const username = $('<a>')
        .attr('href', `/profile/${user.username}`)
        .text(user.username);
    const name = $('<small>')
        .addClass('text-muted d-block')
        .text(user.name || '');
    info.append(username, name);
    
    const followBtn = $('<button>')
        .addClass('btn btn-sm btn-primary')
        .text('Theo dõi')
        .click(function() {
            $.post(`/api/accounts/${user.username}/follow/`, function() {
                followBtn.prop('disabled', true).text('Đã theo dõi');
            });
        });
    
    div.append(avatar, info, followBtn);
    return div;
}

// Initialize when document is ready
$(document).ready(function() {
    // Load initial data
    loadPosts();
    loadNotifications();
    loadFriendSuggestions();
    
    // Handle post form submission
    $('form[action="/api/posts/"]').submit(function(e) {
        e.preventDefault();
        const form = $(this);
        const formData = new FormData(this);
        
        $.ajax({
            url: form.attr('action'),
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function() {
                form.trigger('reset');
                loadPosts();
            }
        });
    });
}); 