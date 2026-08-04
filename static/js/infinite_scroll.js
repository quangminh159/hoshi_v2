/**
 * Feed infinite scroll — mọi bài viết đều render qua JS
 */
(function () {
    'use strict';

    const postsContainer = document.getElementById('posts-container');
    if (!postsContainer) return;

    let isLoading = false;
    let hasMore = true;
    let currentPage = parseInt(document.querySelector('meta[name="current-page"]')?.content || '0', 10);
    const feedType = document.querySelector('meta[name="feed-type"]')?.content || 'diverse';
    const loadedPostIds = new Set();

    const loadingIndicator = document.getElementById('loading-indicator');
    const endMessage = document.getElementById('end-message');
    const emptyMessage = document.getElementById('empty-message');

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function buildFeedUrl(page) {
        const profileUsername = document.querySelector('meta[name="profile-username"]')?.content;
        if (profileUsername) {
            const tab = document.querySelector('meta[name="profile-tab"]')?.content || 'posts';
            return `/users/api/${encodeURIComponent(profileUsername)}/posts/?page=${page}&tab=${encodeURIComponent(tab)}`;
        }
        const path = window.location.pathname;
        if (path.includes('/saved')) {
            return `${path}?page=${page}&format=json`;
        }
        if (path.includes('/liked')) {
            return `${path}?page=${page}&format=json`;
        }
        return `/posts/?page=${page}&feed=${feedType}&format=json`;
    }

    function timeAgo(date) {
        const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
        if (seconds < 60) return 'vừa xong';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} phút`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} giờ`;
        const days = Math.floor(hours / 24);
        if (days < 30) return `${days} ngày`;
        const months = Math.floor(days / 30);
        if (months < 12) return `${months} tháng`;
        return `${Math.floor(months / 12)} năm`;
    }

    function profileUrl(username) {
        return `/users/${encodeURIComponent(username)}/`;
    }

    function formatCaption(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/#(\w+)/g, '<a href="/posts/search/?q=$1" class="hashtag-link" onclick="event.stopPropagation()">#$1</a>')
            .replace(/@(\w+)/g, (_, u) => `<a href="${profileUrl(u)}" class="mention-link" onclick="event.stopPropagation()">@${u}</a>`)
            .replace(/\n/g, '<br>');
    }

    function createPostElement(post) {
        const postDiv = document.createElement('div');
        postDiv.className = 'card feed-post-card';
        postDiv.id = `post-${post.id}`;

        function mediaUrlWithCache(media, cacheVersion) {
            const v = cacheVersion || Date.now();
            const sep = media.file_url.includes('?') ? '&' : '?';
            return `${media.file_url}${sep}v=${v}-${media.id}`;
        }

        function buildMediaCarousel(mediaList, carouselId, clickUrl, cacheVersion) {
            if (!mediaList || mediaList.length === 0) return '';
            const slides = mediaList.map((media, index) => `
                <div class="carousel-item ${index === 0 ? 'active' : ''}">
                    ${media.media_type === 'image'
                        ? `<img src="${mediaUrlWithCache(media, cacheVersion)}" class="d-block w-100" alt="Post image" loading="lazy" decoding="async">`
                        : `<video class="d-block w-100 feed-video" muted loop playsinline preload="metadata" controls src="${mediaUrlWithCache(media, cacheVersion)}" onclick="event.stopPropagation()"></video>`
                    }
                </div>
            `).join('');

            const indicators = mediaList.length > 1 ? `
                <div class="carousel-indicators">
                    ${mediaList.map((_, index) => `
                        <button type="button" data-bs-target="#${carouselId}" data-bs-slide-to="${index}"
                            ${index === 0 ? 'class="active" aria-current="true"' : ''} aria-label="Slide ${index + 1}"></button>
                    `).join('')}
                </div>` : '';

            const controls = mediaList.length > 1 ? `
                <button class="carousel-control-prev" type="button" data-bs-target="#${carouselId}" data-bs-slide="prev" onclick="event.stopPropagation();">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#${carouselId}" data-bs-slide="next" onclick="event.stopPropagation();">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                </button>` : '';

            return `
                <div id="${carouselId}" class="carousel slide post-content" data-bs-ride="false"
                     onclick="window.location='${clickUrl}'" style="cursor:pointer;">
                    ${indicators}
                    <div class="carousel-inner">${slides}</div>
                    ${controls}
                </div>`;
        }

        let sharedHTML = '';
        const mediaCacheVersion = post.updated_at ? new Date(post.updated_at).getTime() : post.id;
        if (post.shared_from) {
            const original = post.shared_from;
            const originalMedia = buildMediaCarousel(
                original.media,
                `carousel-shared-${post.id}`,
                `/posts/${original.id}/`,
                original.updated_at ? new Date(original.updated_at).getTime() : original.id
            );
            sharedHTML = `
                <div class="shared-post-container border rounded bg-white">
                    <div class="share-title p-2 border-bottom">
                        <i class="fas fa-retweet text-primary me-1"></i>
                        <span class="text-muted">Đã chia sẻ bài viết</span>
                    </div>
                    <div class="shared-post-header" style="cursor:pointer;" onclick="window.location='/posts/${original.id}/';">
                        <div class="d-flex align-items-center mb-2">
                            <img src="${original.author.avatar}" class="rounded-circle me-2" width="32" height="32"
                                 alt="${original.author.username}" loading="lazy">
                            <div>
                                <a href="${profileUrl(original.author.username)}"
                                   class="text-dark text-decoration-none fw-bold"
                                   onclick="event.stopPropagation();">${original.author.username}</a>
                                ${original.location ? `<div class="text-muted small">${original.location}</div>` : ''}
                            </div>
                        </div>
                        ${original.caption ? `<p class="card-text mb-0">${formatCaption(original.caption)}</p>` : ''}
                    </div>
                    <div class="shared-post-media">
                        ${originalMedia}
                    </div>
                </div>`;
        }

        const mediaHTML = post.shared_from
            ? ''
            : buildMediaCarousel(post.media, `carousel-${post.id}`, `/posts/${post.id}/`, mediaCacheVersion);

        postDiv.innerHTML = `
            <div class="feed-post-body">
                <div class="feed-post-avatar-col">
                    <a href="${profileUrl(post.author.username)}" class="feed-post-avatar-link" onclick="event.stopPropagation();">
                        <img src="${post.author.avatar}" class="rounded-circle feed-post-avatar"
                             alt="${post.author.username}" loading="lazy">
                    </a>
                </div>
                <div class="feed-post-main">
                    <div class="feed-post-meta" style="cursor:pointer;" onclick="window.location='/posts/${post.id}/';">
                        <div class="feed-post-meta-left">
                            <a href="${profileUrl(post.author.username)}"
                               class="text-dark text-decoration-none fw-bold feed-post-username"
                               onclick="event.stopPropagation();">${post.author.username}</a>
                            <span class="text-muted small feed-post-time">${timeAgo(new Date(post.created_at))}</span>
                            ${post.shared_from ? `<span class="text-muted small"><i class="fas fa-retweet me-1"></i>đã chia sẻ</span>` : ''}
                        </div>
                    </div>
                    ${post.caption ? `
                    <div class="feed-post-caption post-content" onclick="window.location='/posts/${post.id}/';" style="cursor:pointer;">
                        <p class="card-text mb-0">${formatCaption(post.caption)}</p>
                    </div>` : ''}
                    ${sharedHTML}
                    ${mediaHTML}
                    <div class="card-footer d-flex justify-content-between py-2 bg-white feed-post-actions">
                        <div class="d-flex align-items-center">
                            <button class="btn btn-light btn-sm me-2 like-button ${post.is_liked ? 'liked' : ''}" data-post-id="${post.id}">
                                <i class="${post.is_liked ? 'fas' : 'far'} fa-heart"></i>
                                ${post.hide_likes ? '' : `<span class="likes-count" data-post-id="${post.id}">${post.likes_count}</span>`}
                            </button>
                            <a href="/posts/${post.id}/" class="btn btn-light btn-sm me-2">
                                <i class="far fa-comment"></i>
                                <span>${post.comments_count}</span>
                            </a>
                            <button class="btn btn-light btn-sm share-button" data-post-id="${post.id}"
                                    data-bs-toggle="modal" data-bs-target="#sharePostModal"
                                    title="Chia sẻ" aria-label="Chia sẻ">
                                <i class="far fa-share-square"></i>
                            </button>
                        </div>
                        <button class="btn btn-light btn-sm save-button" data-post-id="${post.id}">
                            <i class="${post.is_saved ? 'fas' : 'far'} fa-bookmark"></i>
                        </button>
                    </div>
                    <div class="comments-section px-0 pb-1">
                        ${post.disable_comments
                            ? '<p class="text-muted small mb-2">Bài viết này đã tắt bình luận.</p>'
                            : `<div class="root-comments-list">${renderCommentsHtml(post)}</div>
                        ${buildLoadMoreCommentsHtml(post)}`}
                    </div>
                    ${post.disable_comments ? '' : `
                    <form class="mt-3 add-comment-form" data-post-id="${post.id}" data-no-auto="true" data-ajax-submit="true" enctype="multipart/form-data">
                        <div class="comment-image-preview d-none mb-2">
                            <div class="comment-image-preview-inner">
                                <img src="" alt="Xem trước ảnh" class="comment-preview-thumb">
                                <button type="button" class="btn btn-sm btn-light comment-image-clear" title="Xóa ảnh">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                        <div class="input-group">
                            <label class="btn btn-light border comment-image-btn mb-0" title="Đính kèm ảnh" for="comment-image-${post.id}">
                                <i class="far fa-image"></i>
                            </label>
                            <input type="file" class="d-none comment-image-input" id="comment-image-${post.id}" name="image" accept="image/*">
                            <input type="text" name="text" id="comment-input-${post.id}" class="form-control comment-input"
                                   placeholder="Viết bình luận..." aria-label="Comment input" autocomplete="off">
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
                    </form>`}
                </div>
            </div>`;

        if (post.is_liked) localStorage.setItem(`post_liked_${post.id}`, 'true');
        if (post.is_saved) localStorage.setItem(`post_saved_${post.id}`, 'true');

        return postDiv;
    }

    function restoreInteractionStates() {
        document.querySelectorAll('.like-button').forEach((button) => {
            const postId = button.getAttribute('data-post-id');
            const icon = button.querySelector('i');
            if (!postId || !icon) return;
            const liked = localStorage.getItem(`post_liked_${postId}`) === 'true';
            icon.className = liked ? 'fas fa-heart' : 'far fa-heart';
            button.classList.toggle('liked', liked);
        });

        document.querySelectorAll('.save-button').forEach((button) => {
            const postId = button.getAttribute('data-post-id');
            const icon = button.querySelector('i');
            if (!postId || !icon) return;
            const saved = localStorage.getItem(`post_saved_${postId}`) === 'true';
            icon.className = saved ? 'fas fa-bookmark' : 'far fa-bookmark';
        });
    }

    function likePost(postId) {
        const button = document.querySelector(`.like-button[data-post-id="${postId}"]`);
        if (!button) return;
        const icon = button.querySelector('i');
        const countEl = button.querySelector('.likes-count');
        const wasLiked = icon.classList.contains('fas');
        const prevCount = countEl ? parseInt(countEl.textContent, 10) || 0 : 0;

        icon.className = wasLiked ? 'far fa-heart' : 'fas fa-heart';
        button.classList.toggle('liked', !wasLiked);
        if (countEl) countEl.textContent = wasLiked ? Math.max(0, prevCount - 1) : prevCount + 1;
        if (wasLiked) localStorage.removeItem(`post_liked_${postId}`);
        else localStorage.setItem(`post_liked_${postId}`, 'true');

        fetch(`/api/posts/${postId}/like/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        })
        .then((r) => r.json())
        .then((data) => {
            document.querySelectorAll(`.like-button[data-post-id="${postId}"]`).forEach((btn) => {
                const heart = btn.querySelector('i');
                if (data.status === 'liked') {
                    heart.className = 'fas fa-heart';
                    btn.classList.add('liked');
                    localStorage.setItem(`post_liked_${postId}`, 'true');
                } else {
                    heart.className = 'far fa-heart';
                    btn.classList.remove('liked');
                    localStorage.removeItem(`post_liked_${postId}`);
                }
            });
            document.querySelectorAll(`.likes-count[data-post-id="${postId}"]`).forEach((el) => {
                el.textContent = data.likes_count;
            });
        })
        .catch(() => {
            icon.className = wasLiked ? 'fas fa-heart' : 'far fa-heart';
            button.classList.toggle('liked', wasLiked);
            if (countEl) countEl.textContent = prevCount;
        });
    }

    function savePost(postId) {
        const button = document.querySelector(`.save-button[data-post-id="${postId}"]`);
        if (!button) return;
        const icon = button.querySelector('i');
        const wasSaved = icon.classList.contains('fas');

        icon.className = wasSaved ? 'far fa-bookmark' : 'fas fa-bookmark';
        if (wasSaved) localStorage.removeItem(`post_saved_${postId}`);
        else localStorage.setItem(`post_saved_${postId}`, 'true');

        fetch(`/api/posts/${postId}/save/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        })
        .then((r) => r.json())
        .then((data) => {
            document.querySelectorAll(`.save-button[data-post-id="${postId}"]`).forEach((btn) => {
                const bookmark = btn.querySelector('i');
                if (data.status === 'saved') {
                    bookmark.className = 'fas fa-bookmark';
                    localStorage.setItem(`post_saved_${postId}`, 'true');
                } else {
                    bookmark.className = 'far fa-bookmark';
                    localStorage.removeItem(`post_saved_${postId}`);
                }
            });
        })
        .catch(() => {
            icon.className = wasSaved ? 'fas fa-bookmark' : 'far fa-bookmark';
        });
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function formatCommentTime(createdAt) {
        if (!createdAt) return 'vừa xong';
        let date = createdAt;
        if (typeof createdAt === 'string' && createdAt.includes('/')) {
            const m = createdAt.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
            if (m) {
                const [, d, mo, y, h = '0', min = '0'] = m;
                date = new Date(`${y}-${mo}-${d}T${h}:${min}:00`);
            } else {
                return createdAt;
            }
        }
        try {
            const t = timeAgo(new Date(date));
            return t === 'vừa xong' ? t : `${t} trước`;
        } catch {
            return 'vừa xong';
        }
    }

    function commentImageHtml(comment) {
        const url = comment.image_url || comment.image;
        if (!url) return '';
        return `<div class="comment-image-wrap mt-1">
            <a href="${escapeHtml(url)}" target="_blank" rel="noopener">
                <img src="${escapeHtml(url)}" alt="Ảnh bình luận" class="comment-image">
            </a>
        </div>`;
    }

    function buildRootCommentBodyHtml(comment, postId) {
        const username = comment.author_username || comment.author?.username || 'user';
        const commentId = comment.id;
        const isLiked = comment.is_liked === true;
        const likesCount = comment.likes_count || 0;
        const likeLabel = isLiked ? 'Đã thích' : 'Thích';
        const likeBtnClass = isLiked ? 'text-primary' : 'text-muted';
        const timeLabel = formatCommentTime(comment.created_at);
        const likesHtml = likesCount > 0 ? `
            <span class="ms-2 comment-likes-wrap">
                <i class="fas fa-heart text-danger small"></i>
                <span class="comment-likes-count" data-comment-id="${commentId}">${likesCount}</span>
            </span>` : '';

        return `
            <a href="${profileUrl(username)}" class="text-dark text-decoration-none fw-bold">${escapeHtml(username)}</a>
            ${comment.text ? `<span class="ms-1">${escapeHtml(comment.text)}</span>` : ''}
            ${commentImageHtml(comment)}
            <div class="text-muted small d-flex align-items-center flex-wrap mt-1">
                <span>${timeLabel}</span>
                <span class="mx-1">·</span>
                <button type="button" class="btn btn-link btn-sm p-0 comment-like-button ${likeBtnClass}"
                        data-comment-id="${commentId}">
                    <span>${likeLabel}</span>
                </button>
                <span class="mx-1">·</span>
                <button type="button" class="btn btn-link btn-sm p-0 text-muted reply-button"
                        data-username="${escapeHtml(username)}"
                        data-post-id="${postId}"
                        data-comment-id="${commentId}">
                    Trả lời
                </button>
                ${likesHtml}
            </div>`;
    }

    function buildReplyHtml(comment, postId) {
        const username = comment.author_username || comment.author?.username || 'user';
        const commentId = comment.id;
        const isLiked = comment.is_liked === true;
        const likesCount = comment.likes_count || 0;
        const likeLabel = isLiked ? 'Đã thích' : 'Thích';
        const likeBtnClass = isLiked ? 'text-primary' : 'text-muted';
        const timeLabel = formatCommentTime(comment.created_at);
        const likesHtml = likesCount > 0 ? `
            <span class="ms-2 comment-likes-wrap">
                <i class="fas fa-heart text-danger small"></i>
                <span class="comment-likes-count" data-comment-id="${commentId}">${likesCount}</span>
            </span>` : '';

        return `
            <div class="comment reply-comment mb-2" id="comment-${commentId}" data-comment-id="${commentId}">
                <a href="${profileUrl(username)}" class="text-dark text-decoration-none fw-bold">${escapeHtml(username)}</a>
                ${comment.text ? `<span class="ms-1">${escapeHtml(comment.text)}</span>` : ''}
                ${commentImageHtml(comment)}
                <div class="text-muted small d-flex align-items-center flex-wrap mt-1">
                    <span>${timeLabel}</span>
                    <span class="mx-1">·</span>
                    <button type="button" class="btn btn-link btn-sm p-0 comment-like-button ${likeBtnClass}"
                            data-comment-id="${commentId}">
                        <span>${likeLabel}</span>
                    </button>
                    <span class="mx-1">·</span>
                    <button type="button" class="btn btn-link btn-sm p-0 text-muted reply-button"
                            data-username="${escapeHtml(username)}"
                            data-post-id="${postId}"
                            data-comment-id="${commentId}">
                        Trả lời
                    </button>
                    ${likesHtml}
                </div>
            </div>`;
    }

    function buildCommentHtml(comment, postId, isReply = false) {
        if (isReply) return buildReplyHtml(comment, postId);
        return buildRootCommentWithReplies(comment, postId);
    }

    function buildLoadMoreRepliesHtml(comment, postId) {
        const total = comment.replies_count ?? (comment.replies?.length || 0);
        const shown = comment.replies?.length || 0;
        if (!comment.has_more_replies && total <= shown) return '';
        const remaining = total - shown;
        if (remaining <= 0) return '';
        return `
            <button type="button" class="btn btn-link btn-sm p-0 text-muted load-more-replies"
                    data-post-id="${postId}" data-comment-id="${comment.id}"
                    data-offset="${shown}" data-total="${total}">
                Xem thêm ${remaining} phản hồi
            </button>`;
    }

    function buildRootCommentWithReplies(comment, postId) {
        const commentId = comment.id;
        const replies = comment.replies || [];
        const repliesHtml = replies.map((r) => buildReplyHtml(r, postId)).join('');
        const loadMoreReplies = buildLoadMoreRepliesHtml(comment, postId);
        const hasRepliesBlock = repliesHtml || loadMoreReplies;
        const repliesBlock = hasRepliesBlock ? `
            <div class="comment-replies-block">
                <div class="comment-replies">${repliesHtml}</div>
                ${loadMoreReplies}
            </div>` : '';

        return `
            <div class="comment root-comment mb-2" id="comment-${commentId}" data-comment-id="${commentId}">
                <div class="root-comment-body">${buildRootCommentBodyHtml(comment, postId)}</div>
                ${repliesBlock}
            </div>`;
    }

    function renderCommentsHtml(post) {
        if (!post.comments_data?.length) return '';
        return post.comments_data.map((item) => {
            const data = item.comment || item;
            return buildRootCommentWithReplies(data, post.id);
        }).join('');
    }

    function buildLoadMoreCommentsHtml(post) {
        const shown = post.comments_data?.length || 0;
        const total = post.root_comments_count ?? shown;
        const hasMore = post.has_more_comments ?? (total > shown);
        if (!hasMore || total <= shown) return '';
        const remaining = total - shown;
        return `
            <button type="button" class="btn btn-link btn-sm p-0 text-muted load-more-comments mb-2"
                    data-post-id="${post.id}" data-offset="${shown}" data-total="${total}">
                Xem thêm ${remaining} bình luận
            </button>`;
    }

    function getRootCommentsList(postId) {
        return document.querySelector(`#post-${postId} .root-comments-list`);
    }

    function updateLoadMoreButton(postId, incrementTotal = false) {
        const section = document.querySelector(`#post-${postId} .comments-section`);
        const list = getRootCommentsList(postId);
        const btn = section?.querySelector('.load-more-comments');
        if (!btn || !list) return;
        if (incrementTotal) {
            btn.dataset.total = String((parseInt(btn.dataset.total, 10) || 0) + 1);
        }
        const total = parseInt(btn.dataset.total, 10) || 0;
        const shown = list.querySelectorAll('.root-comment').length;
        if (shown >= total) {
            btn.remove();
            return;
        }
        btn.textContent = `Xem thêm ${total - shown} bình luận`;
    }

    function updateLoadMoreRepliesButton(parentId, incrementTotal = false) {
        const parent = document.getElementById(`comment-${parentId}`);
        const block = parent?.querySelector('.comment-replies-block');
        const repliesBox = block?.querySelector('.comment-replies');
        const btn = block?.querySelector('.load-more-replies');
        if (!btn || !repliesBox) return;
        if (incrementTotal) {
            btn.dataset.total = String((parseInt(btn.dataset.total, 10) || 0) + 1);
        }
        const total = parseInt(btn.dataset.total, 10) || 0;
        const shown = repliesBox.querySelectorAll('.reply-comment').length;
        if (shown >= total) {
            btn.remove();
            return;
        }
        btn.dataset.offset = String(shown);
        btn.textContent = `Xem thêm ${total - shown} phản hồi`;
    }

    function loadMoreReplies(commentId, postId, button) {
        const rootEl = getRootCommentEl(commentId);
        const rootId = rootEl?.dataset.commentId || commentId;
        const offset = parseInt(button.dataset.offset, 10) || 0;
        button.disabled = true;
        button.textContent = 'Đang tải...';

        fetch(`/posts/comments/${rootId}/feed-replies/?offset=${offset}&limit=7`, {
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCsrfToken() },
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Không tải được phản hồi');
            return data;
        })
        .then((data) => {
            const repliesBox = document.querySelector(`#comment-${rootId} .comment-replies`);
            if (!repliesBox) return;

            const existingIds = new Set(
                [...repliesBox.querySelectorAll('.reply-comment[data-comment-id]')]
                    .map((el) => el.dataset.commentId)
            );
            const newReplies = (data.replies || []).filter((r) => !existingIds.has(String(r.id)));
            const html = newReplies.map((r) => buildReplyHtml(r, postId)).join('');
            if (html) {
                repliesBox.insertAdjacentHTML('beforeend', html);
                initPostInteractions(repliesBox);
            }

            if (data.has_more_replies && data.next_offset != null) {
                const total = data.replies_count ?? parseInt(button.dataset.total, 10);
                button.dataset.offset = String(data.next_offset);
                button.dataset.total = String(total);
                const remaining = total - data.next_offset;
                button.textContent = remaining > 0 ? `Xem thêm ${remaining} phản hồi` : 'Xem thêm phản hồi';
                button.disabled = false;
            } else {
                button.remove();
            }
        })
        .catch((err) => {
            console.error('Load replies error:', err);
            button.disabled = false;
            button.textContent = 'Xem thêm phản hồi';
        });
    }

    function loadMoreComments(postId, button) {
        const offset = parseInt(button.dataset.offset, 10) || 0;
        button.disabled = true;
        button.textContent = 'Đang tải...';

        fetch(`/posts/${postId}/feed-comments/?offset=${offset}&limit=7`, {
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCsrfToken() },
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Không tải được bình luận');
            return data;
        })
        .then((data) => {
            const list = getRootCommentsList(postId);
            if (!list) return;

            if (!data.comments_data) {
                console.error('Load comments: unexpected API response', data);
                throw new Error('Phản hồi API không đúng định dạng');
            }

            const existingIds = new Set(
                [...list.querySelectorAll('.root-comment[data-comment-id]')]
                    .map((el) => el.dataset.commentId)
            );
            const newComments = (data.comments_data || []).filter((c) => !existingIds.has(String(c.id)));
            const html = newComments.map((c) => buildRootCommentWithReplies(c, postId)).join('');
            if (html) {
                list.insertAdjacentHTML('beforeend', html);
                initPostInteractions(list);
            }

            const total = data.root_comments_count ?? parseInt(button.dataset.total, 10);
            const shown = list.querySelectorAll('.root-comment').length;
            button.dataset.total = String(total);

            if (shown >= total) {
                button.remove();
                return;
            }

            if (data.has_more_comments && data.next_offset != null) {
                button.dataset.offset = String(data.next_offset);
                button.textContent = `Xem thêm ${total - shown} bình luận`;
                button.disabled = false;
            } else {
                button.remove();
            }
        })
        .catch((err) => {
            console.error('Load comments error:', err);
            button.disabled = false;
            button.textContent = 'Xem thêm bình luận';
        });
    }

    function likeComment(commentId, button) {
        const label = button.querySelector('span');
        const wasLiked = label?.textContent.trim() === 'Đã thích';
        const commentEl = document.getElementById(`comment-${commentId}`);

        if (label) {
            label.textContent = wasLiked ? 'Thích' : 'Đã thích';
            button.classList.toggle('text-primary', !wasLiked);
            button.classList.toggle('text-muted', wasLiked);
        }

        fetch(`/api/posts/comments/${commentId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Lỗi');
            return data;
        })
        .then((data) => {
            if (label) {
                const liked = data.status === 'liked';
                label.textContent = liked ? 'Đã thích' : 'Thích';
                button.classList.toggle('text-primary', liked);
                button.classList.toggle('text-muted', !liked);
            }

            let wrap = commentEl?.querySelector('.comment-likes-wrap');
            if (data.likes_count > 0) {
                if (wrap) {
                    wrap.querySelector('.comment-likes-count').textContent = data.likes_count;
                } else if (commentEl) {
                    const actions = commentEl.querySelector('.text-muted.small');
                    actions?.insertAdjacentHTML('beforeend', `
                        <span class="ms-2 comment-likes-wrap">
                            <i class="fas fa-heart text-danger small"></i>
                            <span class="comment-likes-count" data-comment-id="${commentId}">${data.likes_count}</span>
                        </span>`);
                }
            } else if (wrap) {
                wrap.remove();
            }
        })
        .catch((err) => {
            console.error('Like comment error:', err);
            if (label) {
                label.textContent = wasLiked ? 'Đã thích' : 'Thích';
                button.classList.toggle('text-primary', wasLiked);
                button.classList.toggle('text-muted', !wasLiked);
            }
        });
    }

    function updateFeedCommentCount(postId) {
        const postCard = document.getElementById(`post-${postId}`);
        const countEl = postCard?.querySelector(`a[href="/posts/${postId}/"] span`);
        if (countEl) {
            const current = parseInt(countEl.textContent, 10) || 0;
            countEl.textContent = current + 1;
        }
    }

    function getRootCommentEl(commentId) {
        const el = document.getElementById(`comment-${commentId}`);
        if (!el) return null;
        return el.classList.contains('root-comment') ? el : el.closest('.root-comment');
    }

    function appendCommentToFeed(comment, postId, isReply, parentId) {
        if (comment.is_duplicate) return;

        const postCard = document.getElementById(`post-${postId}`);
        if (!postCard) return;

        const html = isReply
            ? buildReplyHtml(comment, postId)
            : buildRootCommentWithReplies({ ...comment, replies: comment.replies || [] }, postId);
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        const commentEl = wrapper.firstElementChild;

        if (isReply && parentId) {
            const parent = getRootCommentEl(parentId);
            const rootId = parent?.dataset.commentId || parentId;
            let block = parent?.querySelector('.comment-replies-block');
            if (!block && parent) {
                block = document.createElement('div');
                block.className = 'comment-replies-block';
                block.innerHTML = '<div class="comment-replies"></div>';
                parent.appendChild(block);
            }
            const replies = block?.querySelector('.comment-replies');
            const loadMoreBtn = block?.querySelector('.load-more-replies');
            if (loadMoreBtn) {
                loadMoreBtn.insertAdjacentElement('beforebegin', commentEl);
            } else {
                replies?.appendChild(commentEl);
            }
            updateLoadMoreRepliesButton(rootId, true);
        } else {
            let section = postCard.querySelector('.comments-section');
            if (!section) {
                section = document.createElement('div');
                section.className = 'comments-section px-3 pb-1';
                const form = postCard.querySelector('.add-comment-form');
                if (form) postCard.insertBefore(section, form);
                else postCard.appendChild(section);
            }
            let list = section.querySelector('.root-comments-list');
            if (!list) {
                list = document.createElement('div');
                list.className = 'root-comments-list';
                const loadMoreBtn = section.querySelector('.load-more-comments');
                if (loadMoreBtn) section.insertBefore(list, loadMoreBtn);
                else section.appendChild(list);
            }
            list.appendChild(commentEl);
            if (!isReply) updateLoadMoreButton(postId, true);
        }

        initPostInteractions(commentEl);
    }

    function addComment(postId, text, parentId, form, imageFile) {
        const submitBtn = form?.querySelector('button[type="submit"]');
        const originalBtnHtml = submitBtn?.innerHTML;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang gửi...';
        }

        const requestId = `feed-${postId}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        const formData = new FormData();
        formData.append('post_id', postId);
        formData.append('text', text || '');
        formData.append('request_id', requestId);
        if (parentId) formData.append('parent_id', parentId);
        if (imageFile) formData.append('image', imageFile);

        fetch('/api/posts/comments/add/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: formData,
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || data.message || 'Không gửi được bình luận');
            }
            return data;
        })
        .then((data) => {
            if (data.comment) {
                const replyParentId = data.comment.parent?.id || data.comment.parent_id || parentId;
                appendCommentToFeed(data.comment, postId, !!replyParentId, replyParentId);
                updateFeedCommentCount(postId);
                const input = document.getElementById(`comment-input-${postId}`);
                if (input) input.value = '';
                const imageInput = form?.querySelector('.comment-image-input');
                if (imageInput) imageInput.value = '';
                const preview = form?.querySelector('.comment-image-preview');
                if (preview) {
                    preview.classList.add('d-none');
                    const thumb = preview.querySelector('.comment-preview-thumb');
                    if (thumb) thumb.src = '';
                }
                const replyInfo = form?.querySelector('.reply-info');
                if (replyInfo) {
                    replyInfo.classList.add('d-none');
                    replyInfo.removeAttribute('data-parent-id');
                }
            } else {
                throw new Error(data.error || 'Không gửi được bình luận');
            }
        })
        .catch((err) => {
            console.error('Comment error:', err);
            alert(err.message || 'Không gửi được bình luận. Vui lòng thử lại.');
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
            }
        });
    }

    function pauseAllFeedVideos(except) {
        document.querySelectorAll('.feed-video').forEach((video) => {
            if (video !== except && !video.paused) {
                video.pause();
            }
        });
    }

    function tryPlayFeedVideo(video) {
        if (!video) return;
        const slide = video.closest('.carousel-item');
        if (slide && !slide.classList.contains('active')) {
            video.pause();
            return;
        }
        video.muted = true;
        pauseAllFeedVideos(video);
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(() => {});
        }
    }

    const videoObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            const video = entry.target;
            if (entry.isIntersecting && entry.intersectionRatio >= 0.45) {
                tryPlayFeedVideo(video);
            } else if (!video.paused) {
                video.pause();
            }
        });
    }, { threshold: [0, 0.45, 0.7] });

    function bindCarouselVideoSync(carousel) {
        if (carousel.dataset.videoSync === 'true') return;
        carousel.dataset.videoSync = 'true';
        carousel.addEventListener('slid.bs.carousel', () => {
            carousel.querySelectorAll('.feed-video').forEach((video) => {
                const slide = video.closest('.carousel-item');
                if (slide && slide.classList.contains('active')) {
                    const rect = video.getBoundingClientRect();
                    const visible = rect.top < window.innerHeight && rect.bottom > 0;
                    if (visible) tryPlayFeedVideo(video);
                } else if (!video.paused) {
                    video.pause();
                }
            });
        });
    }

    function initPostInteractions(root) {
        const scope = root || document;

        scope.querySelectorAll('.carousel:not([data-initialized])').forEach((carousel) => {
            try {
                new bootstrap.Carousel(carousel, { interval: false });
                carousel.setAttribute('data-initialized', 'true');
                bindCarouselVideoSync(carousel);
            } catch (_) { /* bootstrap not ready */ }
        });

        scope.querySelectorAll('.carousel[data-initialized]:not([data-video-sync="true"])').forEach((carousel) => {
            bindCarouselVideoSync(carousel);
        });

        scope.querySelectorAll('.like-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                likePost(button.getAttribute('data-post-id'));
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.save-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                savePost(button.getAttribute('data-post-id'));
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.share-button:not([data-initialized])').forEach((button) => {
            // Remove leftover text label if present (old cached markup)
            button.querySelectorAll('span').forEach((span) => span.remove());
            button.setAttribute('title', 'Chia sẻ');
            button.setAttribute('aria-label', 'Chia sẻ');
            button.addEventListener('click', () => {
                const postId = button.getAttribute('data-post-id');
                const targetSelector = button.getAttribute('data-bs-target');
                const modal = targetSelector
                    ? document.querySelector(targetSelector)
                    : document.getElementById('sharePostModal');
                if (modal && postId) {
                    const input = modal.querySelector('.share-post-id');
                    if (input) input.value = postId;
                }
            });
            button.setAttribute('data-initialized', 'true');
        });

        if (typeof window.initSharePostModals === 'function') {
            window.initSharePostModals(scope);
        }

        scope.querySelectorAll('.add-comment-form:not([data-initialized])').forEach((form) => {
            const imageInput = form.querySelector('.comment-image-input');
            const preview = form.querySelector('.comment-image-preview');
            const clearBtn = form.querySelector('.comment-image-clear');

            if (imageInput && preview && !imageInput.dataset.previewBound) {
                imageInput.dataset.previewBound = '1';
                imageInput.addEventListener('change', () => {
                    const file = imageInput.files && imageInput.files[0];
                    const thumb = preview.querySelector('.comment-preview-thumb');
                    if (!file) {
                        preview.classList.add('d-none');
                        if (thumb) thumb.src = '';
                        return;
                    }
                    if (!file.type.startsWith('image/')) {
                        alert('Chỉ được chọn file ảnh');
                        imageInput.value = '';
                        return;
                    }
                    if (file.size > 5 * 1024 * 1024) {
                        alert('Ảnh bình luận tối đa 5MB');
                        imageInput.value = '';
                        return;
                    }
                    const reader = new FileReader();
                    reader.onload = (ev) => {
                        if (thumb) thumb.src = ev.target.result;
                        preview.classList.remove('d-none');
                    };
                    reader.readAsDataURL(file);
                });
                if (clearBtn) {
                    clearBtn.addEventListener('click', () => {
                        imageInput.value = '';
                        preview.classList.add('d-none');
                        const thumb = preview.querySelector('.comment-preview-thumb');
                        if (thumb) thumb.src = '';
                    });
                }
            }

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const postId = form.getAttribute('data-post-id');
                const input = document.getElementById(`comment-input-${postId}`);
                const text = input?.value.trim() || '';
                const imageFile = imageInput && imageInput.files && imageInput.files[0] ? imageInput.files[0] : null;
                if (!text && !imageFile) return;
                const replyInfo = form.querySelector('.reply-info');
                const parentId = replyInfo && !replyInfo.classList.contains('d-none')
                    ? replyInfo.getAttribute('data-parent-id') : null;
                addComment(postId, text, parentId, form, imageFile);
            });
            form.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.comment-like-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                likeComment(button.getAttribute('data-comment-id'), button);
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.reply-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const postId = button.getAttribute('data-post-id');
                const form = document.querySelector(`.add-comment-form[data-post-id="${postId}"]`);
                if (!form) return;
                const replyInfo = form.querySelector('.reply-info');
                replyInfo.querySelector('.reply-to-username').textContent = button.getAttribute('data-username');
                replyInfo.setAttribute('data-parent-id', button.getAttribute('data-comment-id'));
                replyInfo.classList.remove('d-none');
                document.getElementById(`comment-input-${postId}`)?.focus();
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.cancel-reply:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const postId = button.getAttribute('data-post-id');
                const replyInfo = document.querySelector(`.add-comment-form[data-post-id="${postId}"] .reply-info`);
                replyInfo?.classList.add('d-none');
                replyInfo?.removeAttribute('data-parent-id');
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.load-more-comments:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                loadMoreComments(button.getAttribute('data-post-id'), button);
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.load-more-replies:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                loadMoreReplies(
                    button.getAttribute('data-comment-id'),
                    button.getAttribute('data-post-id'),
                    button
                );
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.feed-video:not([data-observed])').forEach((video) => {
            video.muted = true;
            video.playsInline = true;
            video.setAttribute('data-observed', 'true');
            video.addEventListener('click', (e) => e.stopPropagation());
            videoObserver.observe(video);

            const rect = video.getBoundingClientRect();
            const visible = rect.top < window.innerHeight * 0.85 && rect.bottom > window.innerHeight * 0.15;
            if (visible) {
                tryPlayFeedVideo(video);
            }
        });
    }

    async function loadMorePosts() {
        if (isLoading || !hasMore) return;
        isLoading = true;
        loadingIndicator?.classList.remove('d-none');

        try {
            const nextPage = currentPage + 1;
            const response = await fetch(buildFeedUrl(nextPage));
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            const newPosts = (data.posts || []).filter((p) => !loadedPostIds.has(String(p.id)));

            newPosts.forEach((post) => {
                loadedPostIds.add(String(post.id));
                const el = createPostElement(post);
                postsContainer.appendChild(el);
                initPostInteractions(el);
            });

            currentPage = nextPage;

            if (newPosts.length > 0) {
                emptyMessage?.classList.add('d-none');
                restoreInteractionStates();
            } else if (currentPage === 1 && loadedPostIds.size === 0) {
                emptyMessage?.classList.remove('d-none');
            }

            hasMore = data.has_next === true;

            if (!hasMore) {
                endMessage?.classList.remove('d-none');
                sentinel.remove();
                scrollObserver.disconnect();
            }
        } catch (err) {
            console.error('Feed load error:', err);
        } finally {
            isLoading = false;
            loadingIndicator?.classList.add('d-none');
        }
    }

    function resetAndReload() {
        currentPage = 0;
        hasMore = true;
        loadedPostIds.clear();
        postsContainer.innerHTML = '';
        endMessage?.classList.add('d-none');
        emptyMessage?.classList.add('d-none');

        if (!document.getElementById('scroll-sentinel')) {
            const newSentinel = document.createElement('div');
            newSentinel.id = 'scroll-sentinel';
            newSentinel.style.cssText = 'height:1px;margin:0;';
            postsContainer.parentNode.insertBefore(newSentinel, postsContainer.nextSibling);
            scrollObserver.observe(newSentinel);
        }

        loadMorePosts();
    }

    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    sentinel.style.cssText = 'height:1px;margin:0;';
    postsContainer.parentNode.insertBefore(sentinel, postsContainer.nextSibling);

    const scrollObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !isLoading && hasMore) {
            loadMorePosts();
        }
    }, { rootMargin: '600px', threshold: 0 });

    scrollObserver.observe(sentinel);

    if (sessionStorage.getItem('postsFeedStale') === '1') {
        sessionStorage.removeItem('postsFeedStale');
        resetAndReload();
    } else {
        loadMorePosts();
    }

    window.restoreInteractionStates = restoreInteractionStates;
    window.infiniteScroll = { loadMorePosts, resetAndReload, refresh: restoreInteractionStates };
})();
