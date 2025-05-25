/**
 * Infinite Scroll cho Feed
 * Sử dụng Intersection Observer API để tải tự động khi cuộn
 */
document.addEventListener('DOMContentLoaded', function() {
    // Biến để kiểm soát trạng thái
    let isLoading = false;
    let hasMorePosts = true;
    let currentPage = parseInt(document.querySelector('meta[name="current-page"]')?.content || '1');
    let feedType = document.querySelector('meta[name="feed-type"]')?.content || 'diverse';
    let loadedPostIds = new Set(); 
    let totalPosts = parseInt(document.querySelector('meta[name="total-posts"]')?.content || '0');
    let retryCount = 0; 
    const MAX_RETRIES = 5; 
    let consecutiveDuplicates = 0;
    const MAX_CONSECUTIVE_DUPLICATES = 2;
    let missingPostsDetected = false; 
    
    console.log(`Infinite scroll initialized with page=${currentPage}, feedType=${feedType}, totalPosts=${totalPosts}`);
    
    // Lưu trữ các ID bài viết đã tải sẵn
    document.querySelectorAll('.card[id^="post-"]').forEach(post => {
        const postId = post.id.replace('post-', '');
        if (postId) {
            loadedPostIds.add(postId);
        }
    });
    console.log(`Đã tìm thấy ${loadedPostIds.size} bài viết đã tải trước đó`);
    console.log('Danh sách ID bài viết hiện có:', Array.from(loadedPostIds));
    
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
    
    // Tạo phần tử hiển thị thông tin số lượng bài viết
    const statusInfoDiv = document.createElement('div');
    statusInfoDiv.id = 'posts-status-info';
    statusInfoDiv.className = 'd-flex justify-content-between align-items-center px-2 py-1 bg-light rounded mb-3';
    statusInfoDiv.style.display = 'none'; // Ẩn div này đi

    // Xóa nội dung cũ và để trống
    statusInfoDiv.innerHTML = '';

    // Chèn phần tử thông tin vào đầu container
    if (postsContainer && postsContainer.parentNode) {
        postsContainer.parentNode.insertBefore(statusInfoDiv, postsContainer);
    }
    
    // Tạo phần tử chứa thông tin debug (ẩn mặc định)
    const debugInfoDiv = document.createElement('div');
    debugInfoDiv.id = 'debug-info-panel';
    debugInfoDiv.className = 'card mb-3 d-none';
    debugInfoDiv.innerHTML = `
        <div class="card-header bg-light">
            <h6 class="mb-0">Thông tin chi tiết về bài viết</h6>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Tổng số bài viết:</strong> <span id="debug-total-posts">${totalPosts || 'Không xác định'}</span></p>
                    <p><strong>Đã tải:</strong> <span id="debug-loaded-posts">${loadedPostIds.size}</span></p>
                    <p><strong>Trang hiện tại:</strong> <span id="debug-current-page">${currentPage}</span></p>
                    <p><strong>Loại feed:</strong> <span id="debug-feed-type">${feedType}</span></p>
                </div>
                <div class="col-md-6">
                    <p><strong>Còn thiếu:</strong> <span id="debug-missing-posts">${totalPosts ? totalPosts - loadedPostIds.size : 'Không xác định'}</span></p>
                    <p><strong>Tỉ lệ tải:</strong> <span id="debug-load-percentage">${totalPosts ? Math.round(loadedPostIds.size/totalPosts*100) + '%' : 'Không xác định'}</span></p>
                    <p><strong>Số lần thử lại:</strong> <span id="debug-retry-count">${retryCount}/${MAX_RETRIES}</span></p>
                    <p><strong>Còn bài viết mới:</strong> <span id="debug-has-more">${hasMorePosts ? 'Có' : 'Không'}</span></p>
                </div>
            </div>
            <div class="mt-3">
                <button class="btn btn-sm btn-primary" id="debug-load-missing">Tìm bài viết bị thiếu</button>
                <button class="btn btn-sm btn-secondary ms-2" id="debug-load-more">Tải trang tiếp theo</button>
                <button class="btn btn-sm btn-outline-danger ms-2" id="debug-reload-page">Tải lại trang</button>
            </div>
        </div>
    `;
    
    // Chèn phần tử debug vào sau phần tử thông tin
    if (statusInfoDiv.parentNode) {
        statusInfoDiv.parentNode.insertBefore(debugInfoDiv, statusInfoDiv.nextSibling);
        
        // Thêm sự kiện cho các nút trong debug panel
        const loadMissingBtn = document.getElementById('debug-load-missing');
        if (loadMissingBtn) {
            loadMissingBtn.addEventListener('click', function() {
                loadMissingPosts();
            });
        }
        
        const loadMoreBtn = document.getElementById('debug-load-more');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', function() {
                if (!isLoading && hasMorePosts) {
                    loadMorePosts();
                } else {
                    showNotification('Không thể tải thêm bài viết', 'warning');
                }
            });
        }
        
        const reloadPageBtn = document.getElementById('debug-reload-page');
        if (reloadPageBtn) {
            reloadPageBtn.addEventListener('click', function() {
                window.location.reload();
            });
        }
    }
    
    // Tạo sentinel element để theo dõi với IntersectionObserver
    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    sentinel.style.height = '10px';
    sentinel.style.margin = '20px 0';
    if (postsContainer) {
        postsContainer.parentNode.insertBefore(sentinel, postsContainer.nextSibling);
    }
    
    // Hàm bật/tắt hiển thị thông tin debug
    function toggleDebugInfo() {
        const debugPanel = document.getElementById('debug-info-panel');
        if (debugPanel) {
            debugPanel.classList.toggle('d-none');
            
            // Cập nhật thông tin mới nhất khi hiển thị
            if (!debugPanel.classList.contains('d-none')) {
                updateDebugInfo();
            }
        }
    }
    
    // Hàm cập nhật thông tin debug
    function updateDebugInfo() {
        document.getElementById('debug-total-posts').textContent = totalPosts || 'Không xác định';
        document.getElementById('debug-loaded-posts').textContent = loadedPostIds.size;
        document.getElementById('debug-current-page').textContent = currentPage;
        document.getElementById('debug-feed-type').textContent = feedType;
        document.getElementById('debug-missing-posts').textContent = totalPosts ? totalPosts - loadedPostIds.size : 'Không xác định';
        document.getElementById('debug-load-percentage').textContent = totalPosts ? Math.round(loadedPostIds.size/totalPosts*100) + '%' : 'Không xác định';
        document.getElementById('debug-retry-count').textContent = `${retryCount}/${MAX_RETRIES}`;
        document.getElementById('debug-has-more').textContent = hasMorePosts ? 'Có' : 'Không';
    }
    
    // Hàm cập nhật thông tin trạng thái
    function updateStatusInfo() {
        const loadedCountElement = document.getElementById('loaded-posts-count');
        if (loadedCountElement) {
            loadedCountElement.textContent = loadedPostIds.size;
        }
        
        const percentageElement = loadedCountElement?.nextElementSibling?.nextElementSibling;
        if (percentageElement && totalPosts) {
            const percentage = Math.round(loadedPostIds.size/totalPosts*100);
            percentageElement.textContent = `${percentage}%`;
            percentageElement.className = `badge ms-1 ${percentage >= 95 ? 'bg-success' : percentage >= 80 ? 'bg-info' : 'bg-warning'}`;
        }
    }
    
    /**
     * Hàm tải thêm bài viết qua API
     */
    async function loadMorePosts() {
        if (isLoading) return;
        
        isLoading = true;
        const loaderElement = document.getElementById('loading-indicator');
        if (loaderElement) {
            loaderElement.classList.remove('d-none');
            loaderElement.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Đang tải...</span>
                </div>
                <p class="mt-2 text-muted">Đã tải ${loadedPostIds.size}${totalPosts ? '/' + totalPosts : ''} bài viết...</p>
            `;
        }
        
        try {
            // Tạo URL với tham số page và feed type
            const nextPage = currentPage + 1;
            const url = `/posts/?page=${nextPage}&feed=${feedType}&format=json`;
            
            // Gửi request đến server
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Server response error: ${response.status}`);
            }
            
            // Xử lý dữ liệu trả về
            const data = await response.json();
            
            // Cập nhật state
            currentPage = nextPage;
            
            // Cập nhật tổng số bài viết từ server
            if (data.total_posts) {
                totalPosts = data.total_posts;
                console.log(`Tổng số bài viết từ server: ${totalPosts}`);
            }
            
            // Lọc và thêm các bài viết mới
            const filteredPosts = data.posts ? data.posts.filter(post => !loadedPostIds.has(post.id.toString())) : [];
            
            if (filteredPosts.length > 0) {
                // Thêm posts vào container
                filteredPosts.forEach(post => {
                    loadedPostIds.add(post.id.toString());
                    const postElement = createPostElement(post);
                    if (postsContainer) {
                        postsContainer.appendChild(postElement);
                    }
                });
                
                // Khởi tạo các tính năng tương tác cho bài viết mới
                initPostInteractions();
                restoreInteractionStates();
                updateStatusInfo();
                updateDebugInfo();
                
                // Reset biến đếm vì đã tìm thấy bài mới
                consecutiveDuplicates = 0;
            } else {
                // Không có bài viết mới, tăng biến đếm
                consecutiveDuplicates++;
                console.log(`Không tìm thấy bài viết mới ở trang ${currentPage} (lần ${consecutiveDuplicates}/${MAX_CONSECUTIVE_DUPLICATES})`);
            }
            
            // Kiểm tra nếu chưa đủ bài viết
            if (totalPosts && loadedPostIds.size < totalPosts) {
                if (consecutiveDuplicates >= MAX_CONSECUTIVE_DUPLICATES) {
                    console.log('Đã thử nhiều lần không có bài mới, thử tìm bài bị thiếu...');
                    setTimeout(() => loadMissingPosts(), 1000);
                } else {
                    // Tiếp tục tải trang tiếp theo
                    setTimeout(() => loadMorePosts(), 500);
                }
            } else {
                // Đã tải đủ bài viết
                console.log(`Đã tải đủ ${loadedPostIds.size}/${totalPosts} bài viết`);
                showEndMessage();
            }
            
        } catch (error) {
            console.error('Lỗi khi tải thêm bài viết:', error);
            
            // Nếu có lỗi và chưa đủ bài viết, thử lại sau 1 giây
            if (totalPosts && loadedPostIds.size < totalPosts) {
                console.log('Thử tải lại sau 1 giây...');
                setTimeout(() => loadMorePosts(), 1000);
            } else {
                showEndMessage();
            }
        } finally {
            isLoading = false;
            if (loaderElement) {
                loaderElement.classList.add('d-none');
            }
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
                <div id="carousel-${post.id}" class="carousel slide post-content" onclick="window.location='/posts/${post.id}/';" style="cursor: pointer;" data-bs-ride="false">
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
                    <button class="carousel-control-prev" 
                            type="button" 
                            data-bs-target="#carousel-${post.id}" 
                            data-bs-slide="prev"
                            onclick="event.stopPropagation();">
                        <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <button class="carousel-control-next" 
                            type="button" 
                            data-bs-target="#carousel-${post.id}" 
                            data-bs-slide="next"
                            onclick="event.stopPropagation();">
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
                                        <span class="mx-1">·</span>
                                        <button class="btn btn-link btn-sm p-0 text-muted reply-button"
                                                data-username="${commentData.comment.author.username}"
                                                data-post-id="${post.id}"
                                                data-comment-id="${commentData.comment.id}">
                                            Trả lời
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // Thêm loại bài viết badge
        let postTypeBadge = '';
        if (post.post_type) {
            if (post.post_type === 'trending') {
                postTypeBadge = `<span class="badge bg-danger"><i class="fas fa-fire"></i> Thịnh hành</span>`;
            } else if (post.post_type === 'recommended') {
                postTypeBadge = `<span class="badge bg-success"><i class="fas fa-thumbs-up"></i> Gợi ý</span>`;
            }
        }
        
        // Render nội dung bài viết - giống feed.html
        postDiv.innerHTML = `
            <!-- Post Header -->
            <div class="card-header bg-white border-0 py-3" style="cursor: pointer;" onclick="window.location='/posts/${post.id}/';">
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center">
                        <img src="${post.author.avatar}" 
                             class="rounded-circle me-2" 
                             width="32" 
                             height="32"
                             alt="${post.author.username}"
                             onerror="this.src='/static/img/default-avatar.png'"
                        >
                        <div>
                            <a href="/accounts/profile/${post.author.username}/" 
                               class="text-dark text-decoration-none fw-bold"
                               onclick="event.stopPropagation();">
                                ${post.author.username}
                            </a>
                            ${post.location ? `
                            <div class="text-muted small">
                                ${post.location}
                            </div>` : ''}
                        </div>
                    </div>
                    <div class="d-flex align-items-center">
                        ${postTypeBadge ? `<div class="post-type-badge me-2">${postTypeBadge}</div>` : ''}
                        <div class="text-muted small">
                            ${timeAgo(new Date(post.created_at))} trước
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Caption -->
            ${post.caption ? `
            <div class="card-body py-2 post-content" onclick="window.location='/posts/${post.id}/';" style="cursor: pointer;">
                <p class="card-text mb-0">
                    ${formatCaption(post.caption)}
                </p>
            </div>
            ` : ''}
            
            <!-- Post Image/Video -->
            ${mediaHTML}
            
            <!-- Post Actions -->
            <div class="card-footer bg-white border-top-0 py-2">
                <div class="d-flex mb-2">
                    <button class="btn btn-link text-dark p-0 me-3 like-button" data-post-id="${post.id}">
                        <i class="${post.is_liked ? 'fas' : 'far'} fa-heart"></i>
                    </button>
                    <a href="/posts/${post.id}/" class="btn btn-link text-dark p-0 me-3">
                        <i class="far fa-comment"></i>
                    </a>
                    <button class="btn btn-link text-dark p-0 me-3 share-button" 
                            data-post-id="${post.id}" 
                            data-bs-toggle="modal" 
                            data-bs-target="#sharePostModal-${post.id}">
                        <i class="far fa-share-square"></i>
                    </button>
                    <button class="btn btn-link text-dark p-0 ms-auto save-button" data-post-id="${post.id}">
                        <i class="${post.is_saved ? 'fas' : 'far'} fa-bookmark"></i>
                    </button>
                </div>
                
                <!-- Likes Count -->
                <div class="mb-2">
                    <span class="fw-bold">${post.likes_count}</span> lượt thích
                </div>
                
                <!-- Comments -->
                ${commentsHTML}
                
                <!-- Comment Form -->
                <form class="mt-3 add-comment-form" data-post-id="${post.id}">
                    <div class="input-group">
                        <input type="text" 
                               id="comment-input-${post.id}"
                               class="form-control comment-input" 
                               placeholder="Viết bình luận..."
                               aria-label="Comment input">
                        <button class="btn btn-primary" type="submit">Gửi</button>
                    </div>
                    <div class="reply-info d-none">
                        <small>
                            Trả lời: <span class="reply-to-username"></span>
                            <button type="button" class="btn btn-link btn-sm p-0 text-muted cancel-reply" data-post-id="${post.id}">
                                <i class="fas fa-times"></i>
                            </button>
                        </small>
                    </div>
                </form>
            </div>
        `;
        
        return postDiv;
    }
    
    /**
     * Khởi tạo sự kiện tương tác cho bài viết mới
     */
    function initPostInteractions() {
        // Khởi tạo carousel
        const carousels = document.querySelectorAll('.carousel:not([data-initialized])');
        carousels.forEach(carousel => {
            try {
                new bootstrap.Carousel(carousel, {
                    interval: false
                });
                carousel.setAttribute('data-initialized', 'true');
            } catch (error) {
                console.error('Error initializing carousel:', error);
            }
        });
        
        // Khởi tạo nút thích
        document.querySelectorAll('.like-button:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const postId = this.getAttribute('data-post-id');
                likePost(postId);
            });
            button.setAttribute('data-initialized', 'true');
        });
        
        // Khởi tạo nút lưu
        document.querySelectorAll('.save-button:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const postId = this.getAttribute('data-post-id');
                savePost(postId);
            });
            button.setAttribute('data-initialized', 'true');
        });
        
        // Khởi tạo form bình luận
        document.querySelectorAll('.add-comment-form:not([data-initialized])').forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const postId = this.getAttribute('data-post-id');
                const commentInput = document.getElementById(`comment-input-${postId}`);
                const text = commentInput.value.trim();
                
                const replyInfo = this.querySelector('.reply-info');
                const isReply = !replyInfo.classList.contains('d-none');
                let parentId = null;
                
                if (isReply) {
                    parentId = replyInfo.getAttribute('data-parent-id');
                }
                
                if (text) {
                    addComment(postId, text, parentId);
                    commentInput.value = '';
                    
                    if (isReply) {
                        // Reset trạng thái trả lời
                        replyInfo.classList.add('d-none');
                        replyInfo.removeAttribute('data-parent-id');
                    }
                }
            });
            form.setAttribute('data-initialized', 'true');
        });
        
        // Kiểm tra và thiết lập các chức năng tương tác khác
        setupCommentInteractions();
    }
    
    // Thiết lập các tương tác với bình luận
    function setupCommentInteractions() {
        // Khởi tạo nút trả lời comment
        document.querySelectorAll('.reply-button:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const postId = this.getAttribute('data-post-id');
                const commentId = this.getAttribute('data-comment-id');
                const username = this.getAttribute('data-username');
                
                // Tìm form bình luận
                const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
                if (form) {
                    // Hiển thị thông tin trả lời
                    const replyInfo = form.querySelector('.reply-info');
                    const usernameEl = replyInfo.querySelector('.reply-to-username');
                    
                    usernameEl.textContent = username;
                    replyInfo.setAttribute('data-parent-id', commentId);
                    replyInfo.classList.remove('d-none');
                    
                    // Focus vào ô input
                    const input = document.getElementById(`comment-input-${postId}`);
                    if (input) {
                        input.focus();
                        input.value = '';
                    }
                }
            });
            button.setAttribute('data-initialized', 'true');
        });
        
        // Khởi tạo nút hủy trả lời
        document.querySelectorAll('.cancel-reply:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const postId = this.getAttribute('data-post-id');
                const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
                
                if (form) {
                    const replyInfo = form.querySelector('.reply-info');
                    replyInfo.classList.add('d-none');
                    replyInfo.removeAttribute('data-parent-id');
                }
            });
            button.setAttribute('data-initialized', 'true');
        });
        
        // Khởi tạo nút thích comment
        document.querySelectorAll('.comment-like-button:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const commentId = this.getAttribute('data-comment-id');
                likeComment(commentId);
            });
            button.setAttribute('data-initialized', 'true');
        });
        
        // Khởi tạo nút share
        document.querySelectorAll('.share-button:not([data-initialized])').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const postId = this.getAttribute('data-post-id');
                // Thực hiện hành động copy link hoặc mở modal chia sẻ
                const postUrl = `${window.location.origin}/posts/${postId}/`;
                
                // Copy vào clipboard
                // navigator.clipboard.writeText(postUrl)
                //     .then(() => {
                //         alert('Đã sao chép đường dẫn bài viết!');
                //     })
                //     .catch(err => {
                //         console.error('Không thể sao chép: ', err);
                //     });
            });
            button.setAttribute('data-initialized', 'true');
        });
    }
    
    /**
     * Xử lý sự kiện thích bài viết
     */
    function likePost(postId) {
        const likeButton = document.querySelector(`.like-button[data-post-id="${postId}"]`);
        if (!likeButton) return;
        
        const likeIcon = likeButton.querySelector('i');
        if (!likeIcon) return;
        
        // Đảo trạng thái UI ngay lập tức để phản hồi người dùng
        const isCurrentlyLiked = likeIcon.classList.contains('fas');
        
        // Lấy phần tử hiển thị số lượt thích
        const likesCountElement = likeButton.closest('.card-footer')?.querySelector('.fw-bold');
        const currentLikesCount = likesCountElement ? parseInt(likesCountElement.textContent) : 0;
        
        // Cập nhật UI trước
        if (isCurrentlyLiked) {
            likeIcon.classList.replace('fas', 'far');
            if (likesCountElement) {
                likesCountElement.textContent = Math.max(0, currentLikesCount - 1);
            }
            localStorage.removeItem(`post_liked_${postId}`);
        } else {
            likeIcon.classList.replace('far', 'fas');
            if (likesCountElement) {
                likesCountElement.textContent = currentLikesCount + 1;
            }
            localStorage.setItem(`post_liked_${postId}`, 'true');
        }
        
        // Gửi yêu cầu like/unlike lên server
        fetch(`/api/posts/${postId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log('Like response:', data);
            
            // Cập nhật UI dựa trên phản hồi từ server
            const likeButtons = document.querySelectorAll(`.like-button[data-post-id="${postId}"]`);
            const likeCountElements = document.querySelectorAll(`.likes-count[data-post-id="${postId}"]`);
            
            likeButtons.forEach(button => {
                const heartIcon = button.querySelector('i');
                if (data.status === 'liked') {
                    heartIcon.className = 'fas fa-heart';
                    button.classList.add('liked');
                    // Lưu trạng thái like vào localStorage
                    localStorage.setItem(`post_liked_${postId}`, 'true');
                } else if (data.status === 'unliked') {
                    heartIcon.className = 'far fa-heart';
                    button.classList.remove('liked');
                    // Xóa trạng thái like khỏi localStorage
                    localStorage.removeItem(`post_liked_${postId}`);
                }
            });

            likeCountElements.forEach(element => {
                element.textContent = data.likes_count;
            });
        })
        .catch(error => {
            console.error('Error liking post:', error);
            // Phục hồi UI nếu có lỗi
            if (isCurrentlyLiked) {
                likeIcon.classList.replace('far', 'fas');
                if (likesCountElement) {
                    likesCountElement.textContent = currentLikesCount;
                }
                localStorage.setItem(`post_liked_${postId}`, 'true');
            } else {
                likeIcon.classList.replace('fas', 'far');
                if (likesCountElement) {
                    likesCountElement.textContent = Math.max(0, currentLikesCount - 1);
                }
                localStorage.removeItem(`post_liked_${postId}`);
            }
        });
    }
    
    /**
     * Xử lý sự kiện lưu bài viết
     */
    function savePost(postId) {
        const saveButton = document.querySelector(`.save-button[data-post-id="${postId}"]`);
        if (!saveButton) return;
        
        const saveIcon = saveButton.querySelector('i');
        if (!saveIcon) return;
        
        // Đảo trạng thái UI ngay lập tức
        const isCurrentlySaved = saveIcon.classList.contains('fas');
        
        if (isCurrentlySaved) {
            saveIcon.classList.replace('fas', 'far');
            localStorage.removeItem(`post_saved_${postId}`);
        } else {
            saveIcon.classList.replace('far', 'fas');
            localStorage.setItem(`post_saved_${postId}`, 'true');
        }
        
        // Gửi yêu cầu save/unsave lên server
        fetch(`/api/posts/${postId}/save/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log('Save response:', data);
            
            // Cập nhật UI dựa trên phản hồi từ server
            const saveButtons = document.querySelectorAll(`.save-button[data-post-id="${postId}"]`);
            
            saveButtons.forEach(button => {
                const bookmarkIcon = button.querySelector('i');
                if (data.status === 'saved') {
                    bookmarkIcon.className = 'fas fa-bookmark';
                    // Lưu trạng thái save vào localStorage
                    localStorage.setItem(`post_saved_${postId}`, 'true');
                } else if (data.status === 'unsaved') {
                    bookmarkIcon.className = 'far fa-bookmark';
                    // Xóa trạng thái save khỏi localStorage
                    localStorage.removeItem(`post_saved_${postId}`);
                }
            });
        })
        .catch(error => {
            console.error('Error saving post:', error);
            // Phục hồi UI nếu có lỗi
            if (isCurrentlySaved) {
                saveIcon.classList.replace('far', 'fas');
                localStorage.setItem(`post_saved_${postId}`, 'true');
            } else {
                saveIcon.classList.replace('fas', 'far');
                localStorage.removeItem(`post_saved_${postId}`);
            }
        });
    }
    
    /**
     * Xử lý sự kiện thêm bình luận
     */
    function addComment(postId, text, parentId = null) {
        const formData = new FormData();
        formData.append('text', text);
        
        if (parentId) {
            formData.append('parent_id', parentId);
        }
        
        // Thêm request ID duy nhất để tránh trùng lặp
        const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
        formData.append('request_id', requestId);
        
        // Gửi request với FormData
        fetch(`/posts/${postId}/comment/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData,
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Tìm hoặc tạo phần comment trong bài viết
                const postElement = document.getElementById(`post-${postId}`);
                let commentSection = postElement.querySelector('.comments-section');
                
                if (!commentSection) {
                    // Tạo section mới nếu chưa có
                    commentSection = document.createElement('div');
                    commentSection.className = 'comments-section';
                    
                    // Tìm vị trí đặt section comment
                    const cardFooter = postElement.querySelector('.card-footer');
                    if (cardFooter) {
                        const likesCount = cardFooter.querySelector('.mb-2');
                        if (likesCount) {
                            cardFooter.insertBefore(commentSection, likesCount.nextSibling);
                        } else {
                            cardFooter.appendChild(commentSection);
                        }
                    }
                }
                
                // Tạo HTML cho comment mới
                const isReply = !!parentId;
                const newCommentHtml = `
                    <div class="comment mb-2 ${isReply ? 'ms-4' : ''}" id="comment-${data.id}" ${isReply ? `data-parent-id="${parentId}"` : ''}>
                        <div class="d-flex">
                            <img src="${data.author.avatar || data.author.avatar_url || '/static/images/default-avatar.png'}" 
                                 class="rounded-circle me-2" 
                                 width="32" 
                                 height="32"
                                 alt="${data.author.username}">
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <a href="/users/${data.author.username}/" class="text-dark text-decoration-none fw-bold">
                                            ${data.author.username}
                                        </a>
                                        ${isReply ? `<span class="text-muted mx-1">trả lời</span>` : ''}
                                        ${data.text}
                                    </div>
                                    <div class="dropdown">
                                        <button class="btn btn-link btn-sm p-0 text-muted dropdown-toggle" 
                                                type="button" 
                                                data-bs-toggle="dropdown" 
                                                aria-expanded="false">
                                            <i class="fas fa-ellipsis-h"></i>
                                        </button>
                                        <ul class="dropdown-menu dropdown-menu-end">
                                            <li>
                                                <button class="dropdown-item reply-button" 
                                                        data-username="${data.author.username}"
                                                        data-post-id="${postId}"
                                                        data-comment-id="${data.id}">
                                                    <i class="fas fa-reply me-2"></i>Trả lời
                                                </button>
                                            </li>
                                            <li>
                                                <button class="dropdown-item text-danger delete-comment-btn" 
                                                       data-comment-id="${data.id}">
                                                    <i class="fas fa-trash-alt me-2"></i>Xóa
                                                </button>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="text-muted small d-flex align-items-center mt-1">
                                    <span>bây giờ</span>
                                    <span class="mx-1">·</span>
                                    <button class="btn btn-link btn-sm p-0 text-muted comment-like-button"
                                            data-comment-id="${data.id}">
                                        <span>Thích</span>
                                    </button>
                                    <span class="mx-1">·</span>
                                    <button class="btn btn-link btn-sm p-0 text-muted reply-button"
                                            data-username="${data.author.username}"
                                            data-post-id="${postId}"
                                            data-comment-id="${data.id}">
                                        Trả lời
                                    </button>
                                </div>
                                <div class="comment-replies ps-4 mt-2"></div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Thêm comment vào DOM
                if (parentId) {
                    // Nếu là reply, thêm vào phần replies của comment cha
                    const parentComment = postElement.querySelector(`#comment-${parentId}`);
                    if (parentComment) {
                        let repliesSection = parentComment.querySelector('.comment-replies');
                        if (!repliesSection) {
                            repliesSection = document.createElement('div');
                            repliesSection.className = 'comment-replies ps-4 mt-2';
                            parentComment.querySelector('.flex-grow-1').appendChild(repliesSection);
                        }
                        repliesSection.insertAdjacentHTML('beforeend', newCommentHtml);
                    }
                } else {
                    // Nếu là comment gốc, thêm vào đầu danh sách
                    commentSection.insertAdjacentHTML('afterbegin', newCommentHtml);
                }
                
                // Cập nhật số lượng comment
                const commentCountElement = postElement.querySelector('.comment-button span');
                if (commentCountElement) {
                    const currentCount = parseInt(commentCountElement.textContent) || 0;
                    commentCountElement.textContent = currentCount + 1;
                }
                
                // Khởi tạo lại sự kiện cho các nút mới
                setupCommentInteractions();
                
                // Hiển thị thông báo nếu có
                if (typeof showNotification === 'function') {
                    showNotification('Bình luận đã được thêm thành công', 'success');
                }
            }
        })
        .catch(error => {
            console.error('Error adding comment:', error);
            if (typeof showNotification === 'function') {
                showNotification('Có lỗi khi thêm bình luận', 'error');
            }
        });
    }
    
    /**
     * Xử lý sự kiện thích comment
     */
    function likeComment(commentId) {
        console.log(`Thích comment ID: ${commentId}`);
        const commentLikeButton = document.querySelector(`.comment-like-button[data-comment-id="${commentId}"]`);
        if (!commentLikeButton) return;
        
        const likeText = commentLikeButton.querySelector('span');
        const isCurrentlyLiked = likeText.textContent === 'Đã thích';
        
        // Cập nhật UI trước
        if (isCurrentlyLiked) {
            likeText.textContent = 'Thích';
            commentLikeButton.classList.remove('text-primary');
        } else {
            likeText.textContent = 'Đã thích';
            commentLikeButton.classList.add('text-primary');
        }
        
        // Gửi yêu cầu like/unlike lên server
        fetch(`/comments/${commentId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({})
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Lỗi khi thích comment');
            }
            return response.json();
        })
        .then(data => {
            console.log('Comment like response:', data);
            
            // Cập nhật UI dựa trên phản hồi từ server
            const commentElement = document.getElementById(`comment-${commentId}`);
            if (commentElement) {
                // Cập nhật trạng thái nút thích
                if (data.status === 'liked') {
                    likeText.textContent = 'Đã thích';
                    commentLikeButton.classList.add('text-primary');
                } else {
                    likeText.textContent = 'Thích';
                    commentLikeButton.classList.remove('text-primary');
                }
                
                // Cập nhật số lượng likes
                let likesCountElement = commentElement.querySelector('.comment-likes-count');
                
                if (data.likes_count > 0) {
                    if (likesCountElement) {
                        // Nếu đã có phần tử hiển thị số lượng like, cập nhật giá trị
                        likesCountElement.textContent = data.likes_count;
                    } else {
                        // Nếu chưa có phần tử hiển thị số lượng like, tạo mới
                        const parentElement = commentLikeButton.parentElement;
                        const likesDisplay = document.createElement('span');
                        likesDisplay.className = 'ms-2';
                        likesDisplay.innerHTML = `
                            <i class="fas fa-heart text-danger small"></i>
                            <span class="comment-likes-count" data-comment-id="${commentId}">${data.likes_count}</span>
                        `;
                        parentElement.appendChild(likesDisplay);
                    }
                } else if (likesCountElement) {
                    // Nếu số lượng like = 0 và có phần tử hiển thị, xóa bỏ nó
                    likesCountElement.parentElement.remove();
                }
            }
        })
        .catch(error => {
            console.error('Error liking comment:', error);
            
            // Phục hồi UI nếu có lỗi
            if (isCurrentlyLiked) {
                likeText.textContent = 'Đã thích';
                commentLikeButton.classList.add('text-primary');
            } else {
                likeText.textContent = 'Thích';
                commentLikeButton.classList.remove('text-primary');
            }
            
            if (typeof showNotification === 'function') {
                showNotification('Có lỗi khi thích bình luận', 'error');
            }
        });
    }
    
    /**
     * Hàm hiển thị thông báo (nếu không có trong global)
     */
    function showNotification(message, type = 'info') {
        // Kiểm tra nếu đã có hàm trong global
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
            return;
        }
        
        // Nếu không, tạo hàm riêng
        // Tạo container thông báo nếu chưa tồn tại
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '20px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '1050';
            document.body.appendChild(notificationContainer);
        }

        // Tạo phần tử thông báo
        const notification = document.createElement('div');
        notification.className = `alert alert-${getBootstrapClass(type)} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Thêm thông báo vào container
        notificationContainer.appendChild(notification);

        // Tự động ẩn thông báo sau 3 giây
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150);
        }, 3000);
    }

    // Hàm chuyển đổi loại thông báo sang class Bootstrap
    function getBootstrapClass(type) {
        switch(type) {
            case 'success': return 'success';
            case 'error': return 'danger';
            case 'warning': return 'warning';
            default: return 'info';
        }
    }
    
    /**
     * Khôi phục trạng thái bài viết từ localStorage
     */
    function restoreInteractionStates() {
        console.log('Khôi phục trạng thái like/save từ localStorage');
        
        // Khôi phục trạng thái like
        document.querySelectorAll('.like-button').forEach(button => {
            const postId = button.getAttribute('data-post-id');
            if (!postId) return;
            
            const icon = button.querySelector('i');
            if (!icon) return;
            
            const isLiked = localStorage.getItem(`post_liked_${postId}`) === 'true';
            
            if (isLiked) {
                icon.className = 'fas fa-heart';
                button.classList.add('liked');
            } else {
                icon.className = 'far fa-heart';
                button.classList.remove('liked');
            }
        });
        
        // Khôi phục trạng thái save
        document.querySelectorAll('.save-button').forEach(button => {
            const postId = button.getAttribute('data-post-id');
            if (!postId) return;
            
            const icon = button.querySelector('i');
            if (!icon) return;
            
            const isSaved = localStorage.getItem(`post_saved_${postId}`) === 'true';
            
            if (isSaved) {
                icon.className = 'fas fa-bookmark';
            } else {
                icon.className = 'far fa-bookmark';
            }
        });
    }
    
    /**
     * Format thời gian tương đối
     */
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        let interval = seconds / 31536000;
        if (interval > 1) {
            return Math.floor(interval) + ' năm trước';
        }
        
        interval = seconds / 2592000;
        if (interval > 1) {
            return Math.floor(interval) + ' tháng trước';
        }
        
        interval = seconds / 86400;
        if (interval > 1) {
            return Math.floor(interval) + ' ngày trước';
        }
        
        interval = seconds / 3600;
        if (interval > 1) {
            return Math.floor(interval) + ' giờ trước';
        }
        
        interval = seconds / 60;
        if (interval > 1) {
            return Math.floor(interval) + ' phút trước';
        }
        
        if (seconds < 10) return 'vừa xong';
        
        return Math.floor(seconds) + ' giây trước';
    }
    
    /**
     * Format caption với hashtags và mentions
     */
    function formatCaption(text) {
        if (!text) return '';
        
        // Thêm link cho hashtags và mentions
        return text
            .replace(/#(\w+)/g, '<a href="/posts/explore/?tag=$1" class="text-primary">#$1</a>')
            .replace(/@(\w+)/g, '<a href="/accounts/profile/$1" class="text-primary">@$1</a>');
    }
    
    // Thiết lập Intersection Observer để tải khi cuộn gần đến cuối
    const sentinelElement = document.getElementById('scroll-sentinel');
    if (sentinelElement) {
        const observer = new IntersectionObserver(entries => {
            const [entry] = entries;
            if (entry.isIntersecting && !isLoading && hasMorePosts) {
                console.log('Sentinel is visible, loading more posts');
                loadMorePosts();
            }
        }, {
            root: null, // viewport
            rootMargin: '200px', // trigger khi còn cách 200px
            threshold: 0.1 // trigger khi 10% của sentinel hiển thị
        });
        
        observer.observe(sentinelElement);
        console.log('Đã thiết lập Intersection Observer cho infinite scroll');
        
        // Lưu observer để có thể sử dụng lại sau này
        window.infiniteScrollObserver = observer;
    }
    
    // Khởi tạo tương tác cho các bài viết hiện tại
    initPostInteractions();
    
    // Cập nhật thông tin ban đầu
    updateStatusInfo();
    
    // Hàm hiển thị thông báo hết bài viết
    function showEndMessage() {
        // Kiểm tra xem đã tải đủ số bài viết chưa
        if (totalPosts && loadedPostIds.size < totalPosts * 0.95 && retryCount < MAX_RETRIES) {
            console.log(`Chưa tải đủ bài viết (${loadedPostIds.size}/${totalPosts}), thử tải lại... (lần ${retryCount + 1}/${MAX_RETRIES})`);
            
            // Đặt lại biến hasMorePosts để thử tải lại
            hasMorePosts = true;
            retryCount++;
            
            // Thử tải lại sau 2 giây
            setTimeout(() => loadMorePosts(), 2000);
            return;
        }
        
        const endMsgElement = document.getElementById('end-message');
        if (endMsgElement) {
            endMsgElement.classList.remove('d-none');
            
            // Nếu chưa tải đủ bài viết, hiển thị nút tải lại
            if (totalPosts && loadedPostIds.size < totalPosts * 0.98) {
                console.warn(`Kết thúc tải nhưng vẫn thiếu bài viết: ${loadedPostIds.size}/${totalPosts}`);
                endMsgElement.innerHTML = `
                    <div class="alert alert-warning text-center py-3" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Đã tải ${loadedPostIds.size}/${totalPosts} bài viết (còn thiếu ${totalPosts - loadedPostIds.size} bài).
                        <div class="mt-2">
                            <button class="btn btn-primary btn-sm reload-posts-btn">
                                <i class="fas fa-sync-alt me-1"></i> Tải thêm bài viết
                            </button>
                            <button class="btn btn-outline-secondary btn-sm reload-all-btn ms-2">
                                <i class="fas fa-redo me-1"></i> Tải lại từ đầu
                            </button>
                            ${missingPostsDetected ? `
                            <button class="btn btn-info btn-sm load-missing-btn ms-2">
                                <i class="fas fa-search me-1"></i> Tìm bài viết bị thiếu
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `;
                
                // Thêm sự kiện cho nút tải lại
                setTimeout(() => {
                    const reloadBtn = endMsgElement.querySelector('.reload-posts-btn');
                    if (reloadBtn) {
                        reloadBtn.addEventListener('click', function() {
                            // Reset các biến trạng thái
                            retryCount = 0;
                            hasMorePosts = true;
                            
                            // Ẩn thông báo hết bài
                            endMsgElement.classList.add('d-none');
                            
                            // Tạo lại sentinel element
                            const newSentinel = document.createElement('div');
                            newSentinel.id = 'scroll-sentinel';
                            newSentinel.style.height = '10px';
                            newSentinel.style.margin = '20px 0';
                            if (postsContainer) {
                                postsContainer.parentNode.insertBefore(newSentinel, endMsgElement);
                            }
                            
                            // Thiết lập lại observer
                            if (window.infiniteScrollObserver) {
                                window.infiniteScrollObserver.observe(newSentinel);
                            }
                            
                            // Tải lại bài viết
                            loadMorePosts();
                        });
                    }
                    
                    const reloadAllBtn = endMsgElement.querySelector('.reload-all-btn');
                    if (reloadAllBtn) {
                        reloadAllBtn.addEventListener('click', function() {
                            // Tải lại trang
                            window.location.reload();
                        });
                    }
                    
                    const loadMissingBtn = endMsgElement.querySelector('.load-missing-btn');
                    if (loadMissingBtn) {
                        loadMissingBtn.addEventListener('click', function() {
                            loadMissingPosts();
                        });
                    }
                }, 100);
            } else {
                endMsgElement.innerHTML = `
                    <div class="alert alert-info text-center py-3" role="alert">
                        <i class="fas fa-check-circle me-2"></i>
                        Bạn đã xem hết tất cả ${loadedPostIds.size}/${totalPosts} bài viết (${Math.round(loadedPostIds.size/totalPosts*100)}%)
                    </div>
                `;
            }
        }
        
        const sentinelElement = document.getElementById('scroll-sentinel');
        if (sentinelElement) {
            sentinelElement.remove();
        }
    }
    
    /**
     * Hàm tìm và tải các bài viết bị thiếu
     */
    async function loadMissingPosts() {
        if (isLoading || !totalPosts) return;
        
        isLoading = true;
        console.log('Đang tìm và tải các bài viết bị thiếu...');
        
        // Hiển thị thông báo đang tìm
        showNotification('Đang tìm kiếm bài viết bị thiếu...', 'info');
        
        // Tạo một loading indicator đặc biệt
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            loadingElement.classList.remove('d-none');
            loadingElement.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Đang tìm kiếm...</span>
                </div>
                <p class="mt-2 text-muted">Đang tìm kiếm bài viết bị thiếu...</p>
            `;
        }
        
        try {
            // Tính toán số trang cần tải lại
            const pagesNeeded = Math.ceil(totalPosts / 12); // Giả sử mỗi trang có 12 bài viết
            console.log(`Cần tải lại ${pagesNeeded} trang để đảm bảo đủ ${totalPosts} bài viết`);
            
            // Tải lại từng trang một để tìm bài viết bị thiếu
            let foundNewPosts = false;
            
            // Tạo mảng các trang cần tải
            const pagesToLoad = Array.from({length: pagesNeeded}, (_, i) => i + 1);
            
            // Xáo trộn mảng để tải ngẫu nhiên các trang
            for (let i = pagesToLoad.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [pagesToLoad[i], pagesToLoad[j]] = [pagesToLoad[j], pagesToLoad[i]];
            }
            
            // Hiển thị thứ tự tải trang
            console.log('Thứ tự tải các trang:', pagesToLoad);
            
            // Tải ngẫu nhiên các trang để tìm bài viết bị thiếu
            for (let i = 0; i < pagesToLoad.length; i++) {
                const pageToLoad = pagesToLoad[i];
                
                // Bỏ qua trang hiện tại và trang đầu tiên vì đã tải rồi
                if (pageToLoad === currentPage || pageToLoad === 1) continue;
                
                console.log(`Đang tìm bài viết bị thiếu ở trang ${pageToLoad}/${pagesNeeded}...`);
                
                // Cập nhật trạng thái loading
                if (loadingElement) {
                    loadingElement.querySelector('p').textContent = `Đang tìm bài viết ở trang ${pageToLoad}/${pagesNeeded}...`;
                }
                
                // Tạo URL với tham số page và feed type
                const url = `/posts/?page=${pageToLoad}&feed=${feedType}&format=json`;
                
                // Gửi request đến server
                const response = await fetch(url);
                if (!response.ok) {
                    console.error(`Lỗi khi tải trang ${pageToLoad}: ${response.status}`);
                    continue;
                }
                
                // Xử lý dữ liệu trả về
                const data = await response.json();
                
                // Lọc chỉ thêm các bài viết chưa được hiển thị
                const filteredPosts = data.posts ? data.posts.filter(post => !loadedPostIds.has(post.id.toString())) : [];
                
                if (filteredPosts.length > 0) {
                    console.log(`Tìm thấy ${filteredPosts.length} bài viết mới ở trang ${pageToLoad}`);
                    foundNewPosts = true;
                    
                    // Thêm posts vào container
                    filteredPosts.forEach(post => {
                        // Thêm post ID vào danh sách đã tải
                        loadedPostIds.add(post.id.toString());
                        
                        const postElement = createPostElement(post);
                        if (postsContainer) {
                            postsContainer.appendChild(postElement);
                        }
                    });
                    
                    // Khởi tạo các tính năng tương tác cho bài viết mới
                    initPostInteractions();
                    
                    // Áp dụng trạng thái từ localStorage
                    restoreInteractionStates();
                    
                    // Cập nhật thông tin trạng thái
                    updateStatusInfo();
                    updateDebugInfo();
                    
                    // Hiển thị thông báo tiến trình
                    showNotification(`Đã tìm thấy ${filteredPosts.length} bài viết mới ở trang ${pageToLoad}`, 'success');
                }
                
                // Kiểm tra nếu đã tải đủ bài viết
                if (loadedPostIds.size >= totalPosts * 0.95) {
                    console.log('Đã tải đủ bài viết, dừng tìm kiếm');
                    break;
                }
                
                // Tạm dừng giữa các request để tránh quá tải server
                await new Promise(resolve => setTimeout(resolve, 300));
            }
            
            // Hiển thị kết quả cuối cùng
            if (foundNewPosts) {
                showNotification(`Đã tìm thấy thêm bài viết. Hiện tại: ${loadedPostIds.size}/${totalPosts} (${Math.round(loadedPostIds.size/totalPosts*100)}%)`, 'success');
            } else {
                showNotification('Không tìm thấy thêm bài viết nào', 'warning');
            }
            
            // Cập nhật thông báo cảnh báo
            const warningElement = document.getElementById('warning-message');
            if (warningElement) {
                if (loadedPostIds.size >= totalPosts * 0.95) {
                    warningElement.remove();
                } else {
                    warningElement.innerHTML = `
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Vẫn còn thiếu bài viết (${loadedPostIds.size}/${totalPosts} - ${Math.round(loadedPostIds.size/totalPosts*100)}%). 
                        <div class="mt-2">
                            <button class="btn btn-sm btn-warning reload-page-btn">
                                <i class="fas fa-redo me-1"></i> Tải lại trang
                            </button>
                            <button class="btn btn-sm btn-primary ms-2 load-missing-btn">
                                <i class="fas fa-search me-1"></i> Tiếp tục tìm kiếm
                            </button>
                        </div>
                    `;
                    
                    // Thêm sự kiện cho các nút
                    const reloadBtn = warningElement.querySelector('.reload-page-btn');
                    if (reloadBtn) {
                        reloadBtn.addEventListener('click', function() {
                            window.location.reload();
                        });
                    }
                    
                    const loadMissingBtn = warningElement.querySelector('.load-missing-btn');
                    if (loadMissingBtn) {
                        loadMissingBtn.addEventListener('click', function() {
                            loadMissingPosts();
                        });
                    }
                }
            }
            
            // Cập nhật thông báo hết bài viết nếu đang hiển thị
            const endMsgElement = document.getElementById('end-message');
            if (endMsgElement && !endMsgElement.classList.contains('d-none')) {
                if (loadedPostIds.size >= totalPosts * 0.98) {
                    endMsgElement.innerHTML = `
                        <div class="alert alert-info text-center py-3" role="alert">
                            <i class="fas fa-check-circle me-2"></i>
                            Bạn đã xem hết tất cả ${loadedPostIds.size}/${totalPosts} bài viết (${Math.round(loadedPostIds.size/totalPosts*100)}%)
                        </div>
                    `;
                } else {
                    endMsgElement.innerHTML = `
                        <div class="alert alert-warning text-center py-3" role="alert">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Đã tải ${loadedPostIds.size}/${totalPosts} bài viết (${Math.round(loadedPostIds.size/totalPosts*100)}% - còn thiếu ${totalPosts - loadedPostIds.size} bài).
                            <div class="mt-2">
                                <button class="btn btn-primary btn-sm reload-posts-btn">
                                    <i class="fas fa-sync-alt me-1"></i> Tải thêm bài viết
                                </button>
                                <button class="btn btn-info btn-sm load-missing-btn ms-2">
                                    <i class="fas fa-search me-1"></i> Tìm bài viết bị thiếu
                                </button>
                                <button class="btn btn-outline-secondary btn-sm reload-all-btn ms-2">
                                    <i class="fas fa-redo me-1"></i> Tải lại từ đầu
                                </button>
                            </div>
                        </div>
                    `;
                    
                    // Thêm sự kiện cho các nút
                    setTimeout(() => {
                        const reloadBtn = endMsgElement.querySelector('.reload-posts-btn');
                        if (reloadBtn) {
                            reloadBtn.addEventListener('click', function() {
                                retryCount = 0;
                                hasMorePosts = true;
                                endMsgElement.classList.add('d-none');
                                loadMorePosts();
                            });
                        }
                        
                        const loadMissingBtn = endMsgElement.querySelector('.load-missing-btn');
                        if (loadMissingBtn) {
                            loadMissingBtn.addEventListener('click', function() {
                                loadMissingPosts();
                            });
                        }
                        
                        const reloadAllBtn = endMsgElement.querySelector('.reload-all-btn');
                        if (reloadAllBtn) {
                            reloadAllBtn.addEventListener('click', function() {
                                window.location.reload();
                            });
                        }
                    }, 100);
                }
            }
        } catch (error) {
            console.error('Lỗi khi tìm bài viết bị thiếu:', error);
            showNotification('Có lỗi khi tìm bài viết bị thiếu', 'error');
        } finally {
            isLoading = false;
            const loadingElement = document.getElementById('loading-indicator');
            if (loadingElement) {
                loadingElement.classList.add('d-none');
                loadingElement.innerHTML = `
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Đang tải...</span>
                    </div>
                    <p class="mt-2 text-muted">Đang tải thêm bài viết...</p>
                `;
            }
        }
    }
    
    // Tải tất cả bài viết ngay khi trang được tải
    async function loadAllPosts() {
        if (!totalPosts) return;
        
        console.log('Đang tải tất cả bài viết...');
        const totalPages = Math.ceil(totalPosts / 12); // 12 bài viết mỗi trang
        
        // Tải lần lượt từng trang cho đến khi đủ
        for (let page = 1; page <= totalPages; page++) {
            if (loadedPostIds.size >= totalPosts) break;
            
            // Cập nhật trạng thái loading
            const loadingElement = document.getElementById('loading-indicator');
            if (loadingElement) {
                loadingElement.classList.remove('d-none');
                loadingElement.innerHTML = `
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Đang tải...</span>
                    </div>
                    <p class="mt-2 text-muted">Đang tải trang ${page}/${totalPages}...</p>
                `;
            }
            
            try {
                const url = `/posts/?page=${page}&feed=${feedType}&format=json`;
                const response = await fetch(url);
                if (!response.ok) continue;
                
                const data = await response.json();
                if (!data.posts) continue;
                
                // Lọc và thêm các bài viết mới
                const newPosts = data.posts.filter(post => !loadedPostIds.has(post.id.toString()));
                newPosts.forEach(post => {
                    loadedPostIds.add(post.id.toString());
                    const postElement = createPostElement(post);
                    if (postsContainer) {
                        postsContainer.appendChild(postElement);
                    }
                });
                
                // Cập nhật UI
                initPostInteractions();
                restoreInteractionStates();
                updateStatusInfo();
                updateDebugInfo();
                
                // Chờ một chút trước khi tải trang tiếp theo
                await new Promise(resolve => setTimeout(resolve, 300));
            } catch (error) {
                console.error('Lỗi khi tải trang', page, error);
            }
        }
        
        // Ẩn loading indicator
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            loadingElement.classList.add('d-none');
        }
        
        console.log(`Đã tải xong ${loadedPostIds.size}/${totalPosts} bài viết`);
    }
    
    // Gọi hàm tải tất cả bài viết
    loadAllPosts();
    
    // Biến global để script khác có thể gọi
    window.infiniteScroll = {
        loadMorePosts,
        loadMissingPosts,
        hasMorePosts: () => hasMorePosts,
        currentPage: () => currentPage,
        getLoadedCount: () => loadedPostIds.size,
        getTotalCount: () => totalPosts,
        updateStatusInfo,
        updateDebugInfo,
        toggleDebugInfo
    };
}); 