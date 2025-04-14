/**
 * Infinite Scroll cho Feed
 * Sử dụng cursor-based pagination và Intersection Observer API
 */
document.addEventListener('DOMContentLoaded', function() {
    // Biến để kiểm soát trạng thái
    let isLoading = false;
    let hasMorePosts = true;
    let nextCursor = document.getElementById('next-cursor-value')?.value || null;
    
    // Lấy các phần tử DOM quan trọng
    const postsContainer = document.getElementById('posts-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const endMessage = document.getElementById('end-message');
    
    // Ẩn cảnh báo tải lại trang nếu có bài viết
    const reloadWarning = document.getElementById('reload-warning');
    if (reloadWarning && postsContainer && postsContainer.children.length > 0) {
        reloadWarning.style.display = 'none';
    }
    
    // Tạo phần tử cho loading indicator nếu chưa có
    if (!loadingIndicator && postsContainer) {
        const newLoader = document.createElement('div');
        newLoader.id = 'loading-indicator';
        newLoader.className = 'text-center py-3 d-none';
        newLoader.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Đang tải...</span>
            </div>
            <p class="mt-2 text-muted">Đang tải thêm bài viết...</p>
        `;
        postsContainer.parentNode.insertBefore(newLoader, postsContainer.nextSibling);
    }
    
    // Tạo phần tử thông báo hết bài viết nếu chưa có
    if (!endMessage && postsContainer) {
        const newEndMessage = document.createElement('div');
        newEndMessage.id = 'end-message';
        newEndMessage.className = 'text-center py-3 d-none';
        newEndMessage.innerHTML = `
            <p class="text-muted">Bạn đã xem hết tất cả bài viết</p>
        `;
        postsContainer.parentNode.insertBefore(newEndMessage, postsContainer.nextSibling);
    }
    
    // Tạo sentinel element để theo dõi với IntersectionObserver
    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    sentinel.style.height = '10px';
    if (postsContainer) {
        postsContainer.parentNode.insertBefore(sentinel, postsContainer.nextSibling);
    }
    
    /**
     * Hàm tải thêm bài viết qua API
     */
    async function loadMorePosts() {
        if (isLoading || !hasMorePosts || !nextCursor) return;
        
        isLoading = true;
        document.getElementById('loading-indicator')?.classList.remove('d-none');
        
        try {
            // Tạo URL với cursor
            const url = `/posts/api/posts/load-more/?cursor=${nextCursor}`;
            console.log('Đang tải bài viết tiếp theo từ:', url);
            
            // Gửi request đến server
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Server response error: ${response.status}`);
            }
            
            // Xử lý dữ liệu trả về
            const data = await response.json();
            
            // Cập nhật state
            hasMorePosts = data.has_more;
            nextCursor = data.next_cursor;
            
            // Cập nhật hidden input cursor
            if (document.getElementById('next-cursor-value')) {
                document.getElementById('next-cursor-value').value = nextCursor;
            }
            
            // Nếu không còn post, hiển thị thông báo
            if (!hasMorePosts) {
                document.getElementById('end-message')?.classList.remove('d-none');
                document.getElementById('scroll-sentinel')?.remove();
            }
            
            // Render bài viết mới vào DOM
            if (data.posts && data.posts.length > 0) {
                // Thêm posts vào container
                data.posts.forEach(post => {
                    const postElement = createPostElement(post);
                    postsContainer.appendChild(postElement);
                });
                
                // Khởi tạo các tính năng tương tác cho bài viết mới
                initPostInteractions();
            }
            
            console.log(`Đã tải ${data.posts?.length || 0} bài viết mới, còn thêm: ${hasMorePosts}`);
            
        } catch (error) {
            console.error('Lỗi khi tải thêm bài viết:', error);
        } finally {
            isLoading = false;
            document.getElementById('loading-indicator')?.classList.add('d-none');
        }
    }
    
    /**
     * Tạo HTML cho một bài viết từ dữ liệu JSON
     */
    function createPostElement(post) {
        const postDiv = document.createElement('div');
        postDiv.className = 'card mb-4';
        postDiv.id = `post-${post.id}`;
        
        // Tạo chuỗi HTML cho phần media
        let mediaHTML = '';
        if (post.media && post.media.length > 0) {
            mediaHTML = `
                <div id="carousel-${post.id}" class="carousel slide" data-bs-ride="false">
                    ${post.media.length > 1 ? `
                    <div class="carousel-indicators">
                        ${post.media.map((media, index) => `
                            <button type="button" 
                                data-bs-target="#carousel-${post.id}" 
                                data-bs-slide-to="${index}"
                                ${index === 0 ? 'class="active"' : ''}
                                aria-current="true" 
                                aria-label="Slide ${index + 1}">
                            </button>
                        `).join('')}
                    </div>` : ''}
                    
                    <div class="carousel-inner">
                        ${post.media.map((media, index) => `
                            <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                ${media.media_type === 'image' 
                                    ? `<img src="${media.file_url}" class="d-block w-100" alt="Post image">`
                                    : `<video class="d-block w-100" controls>
                                        <source src="${media.file_url}" type="video/mp4">
                                        Your browser does not support the video tag.
                                      </video>`
                                }
                            </div>
                        `).join('')}
                    </div>
                    
                    ${post.media.length > 1 ? `
                    <button class="carousel-control-prev" type="button" data-bs-target="#carousel-${post.id}" data-bs-slide="prev">
                        <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <button class="carousel-control-next" type="button" data-bs-target="#carousel-${post.id}" data-bs-slide="next">
                        <span class="carousel-control-next-icon" aria-hidden="true"></span>
                        <span class="visually-hidden">Next</span>
                    </button>` : ''}
                </div>
            `;
        }
        
        // Tạo HTML cho phần comments
        let commentsHTML = '';
        if (post.comments_data && post.comments_data.length > 0) {
            commentsHTML = `
                <div class="comments-section">
                    ${post.total_comments > post.comments_data.length ? `
                    <p class="text-muted small mb-2">
                        <a href="/posts/${post.id}/" class="text-decoration-none">
                            Xem tất cả ${post.total_comments} bình luận
                        </a>
                    </p>` : ''}
                    
                    ${post.comments_data.map(commentData => `
                        <div class="comment mb-2" id="comment-${commentData.comment.id}">
                            <div class="d-flex">
                                <div class="flex-grow-1">
                                    <a href="/accounts/profile/${commentData.comment.author.username}/" 
                                       class="text-dark text-decoration-none fw-bold">
                                        ${commentData.comment.author.username}
                                    </a>
                                    ${commentData.comment.text}
                                    
                                    <div class="text-muted small d-flex align-items-center mt-1">
                                        <span>${timeAgo(new Date(commentData.comment.created_at))}</span>
                                        <span class="mx-1">·</span>
                                        <button class="btn btn-link btn-sm p-0 text-muted comment-like-button"
                                                data-comment-id="${commentData.comment.id}">
                                            <span>Thích</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${commentData.replies.map(reply => `
                            <div class="comment mb-2 ps-3" id="comment-${reply.id}">
                                <div class="d-flex">
                                    <div class="flex-grow-1">
                                        <a href="/accounts/profile/${reply.author.username}/" 
                                           class="text-dark text-decoration-none fw-bold">
                                            ${reply.author.username}
                                        </a>
                                        ${reply.text}
                                        
                                        <div class="text-muted small d-flex align-items-center mt-1">
                                            <span>${timeAgo(new Date(reply.created_at))}</span>
                                            <span class="mx-1">·</span>
                                            <button class="btn btn-link btn-sm p-0 text-muted comment-like-button"
                                                    data-comment-id="${reply.id}">
                                                <span>Thích</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    `).join('')}
                </div>
            `;
        }
        
        // Render nội dung bài viết
        postDiv.innerHTML = `
            <!-- Post Header -->
            <div class="card-header bg-white border-0 py-3">
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center">
                        <img src="${post.author.avatar}" 
                             class="rounded-circle me-2" 
                             width="32" 
                             height="32"
                             alt="${post.author.username}"
                        >
                        <div>
                            <a href="/accounts/profile/${post.author.username}/" 
                               class="text-dark text-decoration-none fw-bold">
                                ${post.author.username}
                            </a>
                            ${post.location ? `
                            <div class="text-muted small">
                                ${post.location}
                            </div>` : ''}
                        </div>
                    </div>
                    <div class="text-muted small">
                        ${timeAgo(new Date(post.created_at))}
                    </div>
                </div>
            </div>

            <!-- Caption -->
            ${post.caption ? `
            <div class="card-body py-2">
                <p class="card-text mb-0">
                    ${post.caption}
                </p>
            </div>` : ''}

            <!-- Post Media -->
            ${mediaHTML}

            <!-- Post Actions -->
            <div class="card-body">
                <div class="d-flex mb-2">
                    <button class="btn btn-link text-dark p-0 me-3 like-button" 
                            data-post-id="${post.id}">
                        <i class="${post.is_liked ? 'fas' : 'far'} fa-heart"></i>
                        <span class="likes-count" data-post-id="${post.id}">${post.likes_count}</span>
                    </button>
                    <button class="btn btn-link text-dark p-0 me-3 comment-button"
                            onclick="document.getElementById('comment-input-${post.id}').focus();">
                        <i class="far fa-comment"></i>
                        <span>${post.comments_count}</span>
                    </button>
                    <button class="btn btn-link text-dark p-0 save-button" 
                            data-post-id="${post.id}">
                        <i class="${post.is_saved ? 'fas' : 'far'} fa-bookmark"></i>
                    </button>
                </div>

                <p class="mb-2 likes-count-display">
                    <a href="#" class="text-dark text-decoration-none fw-bold show-likes-button" data-post-id="${post.id}">
                        ${post.likes_count} lượt thích
                    </a>
                </p>

                <!-- Comments -->
                ${commentsHTML}

                <!-- Add Comment -->
                <form class="add-comment-form" data-post-id="${post.id}">
                    <div class="input-group">
                        <input type="text" 
                               id="comment-input-${post.id}"
                               class="form-control border-0 bg-light" 
                               placeholder="Thêm bình luận..."
                               aria-label="Add a comment">
                        <button class="btn btn-link text-primary" type="submit">Đăng</button>
                    </div>
                </form>
            </div>
        `;
        
        return postDiv;
    }
    
    /**
     * Khởi tạo các tính năng tương tác cho bài viết mới
     */
    function initPostInteractions() {
        // Xử lý nút thích
        document.querySelectorAll('.like-button').forEach(button => {
            if (!button.hasListener) {
                button.addEventListener('click', function() {
                    const postId = this.dataset.postId;
                    likePost(postId);
                });
                button.hasListener = true;
            }
        });
        
        // Xử lý nút lưu
        document.querySelectorAll('.save-button').forEach(button => {
            if (!button.hasListener) {
                button.addEventListener('click', function() {
                    const postId = this.dataset.postId;
                    savePost(postId);
                });
                button.hasListener = true;
            }
        });
        
        // Xử lý form bình luận
        document.querySelectorAll('.add-comment-form').forEach(form => {
            if (!form.hasListener) {
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const postId = this.dataset.postId;
                    const input = this.querySelector('input');
                    const comment = input.value.trim();
                    
                    if (comment) {
                        addComment(postId, comment);
                        input.value = '';
                    }
                });
                form.hasListener = true;
            }
        });
        
        // Khởi tạo carousel cho các bài viết mới
        document.querySelectorAll('.carousel').forEach(carousel => {
            if (!carousel.hasBootstrap) {
                new bootstrap.Carousel(carousel, {
                    interval: false
                });
                carousel.hasBootstrap = true;
            }
        });
    }
    
    /**
     * Chức năng thích bài viết
     */
    function likePost(postId) {
        fetch(`/posts/${postId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Cập nhật UI
            const likeButton = document.querySelector(`.like-button[data-post-id="${postId}"]`);
            const likesCount = document.querySelector(`.likes-count[data-post-id="${postId}"]`);
            const likesDisplay = document.querySelector(`#post-${postId} .likes-count-display a`);
            
            if (likeButton && likesCount) {
                const heartIcon = likeButton.querySelector('i');
                
                if (data.liked) {
                    heartIcon.classList.remove('far');
                    heartIcon.classList.add('fas');
                } else {
                    heartIcon.classList.remove('fas');
                    heartIcon.classList.add('far');
                }
                
                likesCount.textContent = data.likes_count;
                
                if (likesDisplay) {
                    likesDisplay.textContent = `${data.likes_count} lượt thích`;
                }
            }
        })
        .catch(error => console.error('Lỗi khi thích bài viết:', error));
    }
    
    /**
     * Chức năng lưu bài viết
     */
    function savePost(postId) {
        fetch(`/posts/${postId}/save/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Cập nhật UI
            const saveButton = document.querySelector(`.save-button[data-post-id="${postId}"]`);
            
            if (saveButton) {
                const bookmarkIcon = saveButton.querySelector('i');
                
                if (data.saved) {
                    bookmarkIcon.classList.remove('far');
                    bookmarkIcon.classList.add('fas');
                } else {
                    bookmarkIcon.classList.remove('fas');
                    bookmarkIcon.classList.add('far');
                }
            }
        })
        .catch(error => console.error('Lỗi khi lưu bài viết:', error));
    }
    
    /**
     * Chức năng thêm bình luận
     */
    function addComment(postId, text) {
        fetch(`/posts/${postId}/comment/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: text })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Refresh lại bài viết hoặc thêm comment vào UI
                window.location.reload();
            }
        })
        .catch(error => console.error('Lỗi khi thêm bình luận:', error));
    }
    
    /**
     * Helper function để lấy CSRF token
     */
    function getCsrfToken() {
        return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
    }
    
    /**
     * Hàm định dạng thời gian
     */
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        let interval = seconds / 31536000;
        if (interval > 1) {
            return Math.floor(interval) + " năm trước";
        }
        
        interval = seconds / 2592000;
        if (interval > 1) {
            return Math.floor(interval) + " tháng trước";
        }
        
        interval = seconds / 86400;
        if (interval > 1) {
            return Math.floor(interval) + " ngày trước";
        }
        
        interval = seconds / 3600;
        if (interval > 1) {
            return Math.floor(interval) + " giờ trước";
        }
        
        interval = seconds / 60;
        if (interval > 1) {
            return Math.floor(interval) + " phút trước";
        }
        
        return "vừa xong";
    }
    
    // Tạo Intersection Observer để theo dõi khi người dùng cuộn đến gần cuối trang
    const intersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !isLoading && hasMorePosts) {
                console.log('Phát hiện cuộn đến sentinel - tải thêm bài viết');
                loadMorePosts();
            }
        });
    }, {
        rootMargin: '0px 0px 300px 0px', // Trigger khi còn 300px nữa đến sentinel
        threshold: 0.1
    });
    
    // Bắt đầu quan sát phần tử sentinel
    if (sentinel) {
        intersectionObserver.observe(sentinel);
        console.log('Đã bắt đầu theo dõi infinite scroll');
    }
    
    // Khởi tạo các tính năng tương tác cho bài viết ban đầu
    initPostInteractions();
}); 