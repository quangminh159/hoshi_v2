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

    // Mỗi lần reload trang HTML → seed mới (thứ tự feed đổi).
    // Trong cùng phiên cuộn infinite scroll → giữ seed để pagination ổn định.
    const FEED_SEED_KEY = 'hoshiFeedSeed';
    const FEED_SEEN_KEY = 'hoshiFeedSeen';
    const FEED_SEEN_MAX = 120;
    const FEED_SEEN_TTL_MS = 3 * 24 * 60 * 60 * 1000; // 3 ngày

    function createFeedSeed() {
        const seed = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        sessionStorage.setItem(FEED_SEED_KEY, seed);
        return seed;
    }
    function getFeedSeed() {
        if (feedType !== 'diverse') return '';
        const freshPage = postsContainer.children.length === 0 && currentPage === 0;
        if (freshPage) return createFeedSeed();
        return sessionStorage.getItem(FEED_SEED_KEY) || createFeedSeed();
    }
    let feedSeed = getFeedSeed();

    function readSeenPosts() {
        try {
            const raw = JSON.parse(localStorage.getItem(FEED_SEEN_KEY) || '[]');
            if (!Array.isArray(raw)) return [];
            const now = Date.now();
            return raw
                .filter((item) => item && item.id != null && now - (item.t || 0) < FEED_SEEN_TTL_MS)
                .slice(-FEED_SEEN_MAX);
        } catch (_) {
            return [];
        }
    }

    function markPostsSeen(postIds) {
        if (!postIds || !postIds.length) return;
        const now = Date.now();
        const map = new Map(readSeenPosts().map((item) => [String(item.id), item.t || now]));
        postIds.forEach((id) => map.set(String(id), now));
        const next = Array.from(map.entries())
            .map(([id, t]) => ({ id, t }))
            .sort((a, b) => a.t - b.t)
            .slice(-FEED_SEEN_MAX);
        try {
            localStorage.setItem(FEED_SEEN_KEY, JSON.stringify(next));
        } catch (_) { /* ignore quota */ }
    }

    function seenQueryParam() {
        if (feedType !== 'diverse') return '';
        const ids = readSeenPosts().map((item) => item.id).slice(-80);
        return ids.length ? ids.join(',') : '';
    }

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
        let url = `/posts/?page=${page}&feed=${feedType}&format=json`;
        if (feedType === 'diverse' && feedSeed) {
            url += `&seed=${encodeURIComponent(feedSeed)}`;
        }
        const seen = seenQueryParam();
        if (seen) {
            url += `&seen=${encodeURIComponent(seen)}`;
        }
        return url;
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
        let html = String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        html = html.replace(/(https?:\/\/[^\s<]+|www\.[^\s<]+)/gi, (raw) => {
            let url = raw;
            let trailing = '';
            while (/[.,;:!?)]+$/.test(url)) {
                trailing = url.slice(-1) + trailing;
                url = url.slice(0, -1);
            }
            if (!url) return raw;
            const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
            return `<a href="${href}" class="caption-link" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">${url}</a>${trailing}`;
        });

        // Mention / hashtag chỉ trên text ngoài thẻ <a>
        html = html.replace(/(<[^>]+>)|([^<]+)/g, (full, tag, textPart) => {
            if (tag) return tag;
            return textPart
                .replace(/#(\w+)/g, '<a href="/posts/search/?q=$1" class="hashtag-link" onclick="event.stopPropagation()">#$1</a>')
                .replace(/@(\w+)/g, (_, u) => `<a href="${profileUrl(u)}" class="mention-link" onclick="event.stopPropagation()">@${u}</a>`);
        });

        return html.replace(/\n/g, '<br>');
    }

    function formatCommentText(text) {
        return formatCaption(text);
    }

    function createPostElement(post) {
        const postDiv = document.createElement('div');
        postDiv.className = 'card feed-post-card';
        postDiv.id = `post-${post.id}`;
        if (post.author?.id) postDiv.setAttribute('data-author-id', post.author.id);

        function mediaUrlWithCache(media, cacheVersion) {
            const v = cacheVersion || Date.now();
            const sep = media.file_url.includes('?') ? '&' : '?';
            return `${media.file_url}${sep}v=${v}-${media.id}`;
        }

        function buildMediaCarousel(mediaList, carouselId, clickUrl, cacheVersion) {
            if (!mediaList || mediaList.length === 0) return '';
            const slides = mediaList.map((media, index) => {
                let body = '';
                if (media.media_type === 'image') {
                    body = `<img src="${mediaUrlWithCache(media, cacheVersion)}" class="d-block w-100" alt="Post image" loading="lazy" decoding="async" style="cursor:zoom-in">`;
                } else if (media.media_type === 'audio') {
                    body = `<div class="post-audio-player" onclick="event.stopPropagation()">
                        <audio class="post-audio" controls preload="metadata" src="${mediaUrlWithCache(media, cacheVersion)}"></audio>
                    </div>`;
                } else {
                    body = `<video class="d-block w-100 feed-video" muted loop playsinline preload="metadata" controls src="${mediaUrlWithCache(media, cacheVersion)}" onclick="event.stopPropagation()" style="cursor:zoom-in"></video>`;
                }
                return `<div class="carousel-item ${index === 0 ? 'active' : ''}">${body}</div>`;
            }).join('');

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

            const audioOnly = mediaList.length > 0 && mediaList.every((m) => m.media_type === 'audio');
            const touchAttr = audioOnly ? ' data-bs-touch="false"' : '';

            return `
                <div id="${carouselId}" class="carousel slide post-content" data-bs-ride="false"${touchAttr}>
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
                            ${post.location ? `<div class="text-muted small feed-post-location"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(post.location)}</div>` : ''}
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
                                <img src="" alt="Xem trước" class="comment-preview-thumb d-none">
                                <video src="" class="comment-preview-video d-none" muted playsinline controls></video>
                                <audio src="" class="comment-preview-audio d-none" controls></audio>
                                <button type="button" class="btn btn-sm btn-light comment-image-clear" title="Xóa đính kèm">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <small class="text-muted d-block mt-1">Ảnh, video ≤ 5s hoặc ghi âm</small>
                        </div>
                        <div class="comment-voice-recording-bar d-none mb-2">
                            <span class="comment-voice-rec-dot" aria-hidden="true"></span>
                            <span class="comment-voice-timer">0:00</span>
                            <span class="comment-voice-hint">Đang ghi âm...</span>
                            <div class="ms-auto d-flex gap-1">
                                <button type="button" class="btn btn-sm btn-light comment-voice-cancel">Hủy</button>
                                <button type="button" class="btn btn-sm btn-primary comment-voice-save">Dùng</button>
                            </div>
                        </div>
                        <div class="input-group">
                            <label class="btn btn-light border comment-image-btn mb-0" title="Đính kèm ảnh/video (≤5s)" for="comment-image-${post.id}">
                                <i class="far fa-image"></i>
                            </label>
                            <button type="button" class="btn btn-light border comment-voice-btn mb-0" title="Ghi âm bình luận">
                                <i class="fas fa-microphone"></i>
                            </button>
                            <input type="file" class="d-none comment-image-input" id="comment-image-${post.id}" name="media" accept="image/*,video/mp4,video/webm,video/quicktime,audio/*">
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
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
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

    function commentVideoHtml(comment) {
        const url = comment.video_url || comment.video;
        if (!url) return '';
        return `<div class="comment-video-wrap mt-1">
            <video class="comment-video" src="${escapeHtml(url)}" controls playsinline preload="metadata"></video>
        </div>`;
    }

    function commentAudioHtml(comment) {
        const url = comment.audio_url || comment.audio;
        if (!url) return '';
        return `<div class="comment-audio-wrap comment-audio-player mt-1">
            <audio class="comment-audio" src="${escapeHtml(url)}" controls preload="metadata"></audio>
        </div>`;
    }

    function commentMediaHtml(comment) {
        return commentImageHtml(comment) + commentVideoHtml(comment) + commentAudioHtml(comment);
    }

    const COMMENT_VIDEO_MAX_SECONDS = 5;
    const COMMENT_VIDEO_MAX_BYTES = 15 * 1024 * 1024;
    const COMMENT_AUDIO_MAX_BYTES = 10 * 1024 * 1024;
    const COMMENT_VOICE_MAX_SECONDS = 120;

    function isCommentAudioFile(file) {
        if (!file) return false;
        const type = (file.type || '').toLowerCase();
        const name = (file.name || '').toLowerCase();
        if (name.startsWith('voice-')) return true;
        if (type.startsWith('audio/')) return true;
        return /\.(m4a|mp3|ogg|wav|aac|flac)$/i.test(name);
    }

    function formatCommentVoiceTimer(seconds) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function pickCommentAudioMimeType() {
        const candidates = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/ogg;codecs=opus',
        ];
        if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return '';
        return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || '';
    }

    function commentAudioMimeToExt(mime) {
        if (!mime) return 'webm';
        if (mime.includes('mp4')) return 'm4a';
        if (mime.includes('ogg')) return 'ogg';
        return 'webm';
    }

    function assignFileToCommentInput(input, file) {
        if (!input || !file) return;
        try {
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;
        } catch (err) {
            console.error('assignFileToCommentInput:', err);
        }
    }

    function clearCommentMediaPreview(form) {
        const preview = form?.querySelector('.comment-image-preview');
        const imageInput = form?.querySelector('.comment-image-input');
        if (form) form._pendingCommentMedia = null;
        if (imageInput) imageInput.value = '';
        if (!preview) return;
        preview.classList.add('d-none');
        const thumb = preview.querySelector('.comment-preview-thumb');
        const videoEl = preview.querySelector('.comment-preview-video');
        const audioEl = preview.querySelector('.comment-preview-audio');
        if (thumb) {
            thumb.src = '';
            thumb.classList.add('d-none');
        }
        if (videoEl) {
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
            videoEl.classList.add('d-none');
        }
        if (audioEl) {
            audioEl.pause();
            if (audioEl.src && audioEl.src.startsWith('blob:')) {
                try { URL.revokeObjectURL(audioEl.src); } catch (_) { /* ignore */ }
            }
            audioEl.removeAttribute('src');
            audioEl.load();
            audioEl.classList.add('d-none');
        }
    }

    function readVideoDuration(file) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const video = document.createElement('video');
            video.preload = 'metadata';
            video.onloadedmetadata = () => {
                const duration = video.duration;
                URL.revokeObjectURL(url);
                resolve(duration);
            };
            video.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('Không đọc được video'));
            };
            video.src = url;
        });
    }

    async function handleCommentMediaSelected(form, file) {
        const preview = form.querySelector('.comment-image-preview');
        if (!preview || !file) {
            clearCommentMediaPreview(form);
            return false;
        }
        const thumb = preview.querySelector('.comment-preview-thumb');
        const videoEl = preview.querySelector('.comment-preview-video');
        const audioEl = preview.querySelector('.comment-preview-audio');
        const imageInput = form.querySelector('.comment-image-input');

        function hidePreviewMedia() {
            if (thumb) {
                thumb.src = '';
                thumb.classList.add('d-none');
            }
            if (videoEl) {
                videoEl.pause();
                videoEl.removeAttribute('src');
                videoEl.load();
                videoEl.classList.add('d-none');
            }
            if (audioEl) {
                audioEl.pause();
                if (audioEl.src && audioEl.src.startsWith('blob:')) {
                    try { URL.revokeObjectURL(audioEl.src); } catch (_) { /* ignore */ }
                }
                audioEl.removeAttribute('src');
                audioEl.load();
                audioEl.classList.add('d-none');
            }
        }

        if (file.type.startsWith('image/')) {
            if (file.size > 5 * 1024 * 1024) {
                alert('Ảnh bình luận tối đa 5MB');
                clearCommentMediaPreview(form);
                return false;
            }
            hidePreviewMedia();
            form._pendingCommentMedia = file;
            assignFileToCommentInput(imageInput, file);
            const reader = new FileReader();
            reader.onload = (ev) => {
                if (thumb) {
                    thumb.src = ev.target.result;
                    thumb.classList.remove('d-none');
                }
                preview.classList.remove('d-none');
            };
            reader.readAsDataURL(file);
            return true;
        }

        if (isCommentAudioFile(file)) {
            if (file.size > COMMENT_AUDIO_MAX_BYTES) {
                alert('Ghi âm bình luận tối đa 10MB');
                clearCommentMediaPreview(form);
                return false;
            }
            hidePreviewMedia();
            form._pendingCommentMedia = file;
            assignFileToCommentInput(imageInput, file);
            if (audioEl) {
                audioEl.src = URL.createObjectURL(file);
                audioEl.classList.remove('d-none');
            }
            preview.classList.remove('d-none');
            return true;
        }

        if (file.type.startsWith('video/')) {
            if (file.size > COMMENT_VIDEO_MAX_BYTES) {
                alert('Video bình luận tối đa 15MB');
                clearCommentMediaPreview(form);
                return false;
            }
            try {
                const duration = await readVideoDuration(file);
                if (!Number.isFinite(duration) || duration > COMMENT_VIDEO_MAX_SECONDS + 0.35) {
                    alert('Video bình luận tối đa 5 giây');
                    clearCommentMediaPreview(form);
                    return false;
                }
            } catch (err) {
                alert(err.message || 'Không đọc được video');
                clearCommentMediaPreview(form);
                return false;
            }
            hidePreviewMedia();
            form._pendingCommentMedia = file;
            assignFileToCommentInput(imageInput, file);
            if (videoEl) {
                videoEl.src = URL.createObjectURL(file);
                videoEl.classList.remove('d-none');
            }
            preview.classList.remove('d-none');
            return true;
        }

        alert('Chỉ chọn ảnh, video ngắn hoặc file ghi âm');
        if (imageInput) imageInput.value = '';
        clearCommentMediaPreview(form);
        return false;
    }

    function bindCommentVoiceRecording(form) {
        if (!form || form.dataset.voiceBound === '1') return;
        form.dataset.voiceBound = '1';

        const voiceBtn = form.querySelector('.comment-voice-btn');
        const voiceBar = form.querySelector('.comment-voice-recording-bar');
        const voiceTimer = form.querySelector('.comment-voice-timer');
        const voiceCancelBtn = form.querySelector('.comment-voice-cancel');
        const voiceSaveBtn = form.querySelector('.comment-voice-save');
        const imageInput = form.querySelector('.comment-image-input');
        if (!voiceBtn || !voiceBar) return;

        let mediaRecorder = null;
        let mediaStream = null;
        let recordedChunks = [];
        let recordingStartedAt = 0;
        let recordingTimerId = null;
        let shouldSaveVoice = false;

        function stopVoiceTracks() {
            if (mediaStream) {
                mediaStream.getTracks().forEach((t) => t.stop());
                mediaStream = null;
            }
        }

        function resetVoiceUI() {
            if (recordingTimerId) {
                clearInterval(recordingTimerId);
                recordingTimerId = null;
            }
            voiceBar.classList.add('d-none');
            if (voiceTimer) voiceTimer.textContent = '0:00';
            voiceBtn.classList.remove('is-recording');
            recordedChunks = [];
            mediaRecorder = null;
            shouldSaveVoice = false;
        }

        function stopCommentVoice(save) {
            shouldSaveVoice = !!save;
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                try { mediaRecorder.stop(); } catch (_) { /* ignore */ }
            } else {
                stopVoiceTracks();
                resetVoiceUI();
            }
        }

        async function startCommentVoice() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
                alert('Trình duyệt không hỗ trợ ghi âm.');
                return;
            }
            if (mediaRecorder && mediaRecorder.state === 'recording') return;

            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err) {
                console.error('Mic permission error:', err);
                alert('Không thể truy cập micro. Hãy cho phép quyền micro rồi thử lại.');
                return;
            }

            recordedChunks = [];
            shouldSaveVoice = false;
            const mime = pickCommentAudioMimeType();
            try {
                mediaRecorder = mime
                    ? new MediaRecorder(mediaStream, { mimeType: mime })
                    : new MediaRecorder(mediaStream);
            } catch (err) {
                console.error('MediaRecorder error:', err);
                stopVoiceTracks();
                alert('Không thể bắt đầu ghi âm trên trình duyệt này.');
                return;
            }

            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                stopVoiceTracks();
                const save = shouldSaveVoice;
                const chunks = recordedChunks.slice();
                const usedMime = (mediaRecorder && mediaRecorder.mimeType) || mime || 'audio/webm';
                resetVoiceUI();

                if (!save) return;
                const blob = new Blob(chunks, { type: usedMime.split(';')[0] });
                if (blob.size < 500) {
                    alert('Bản ghi quá ngắn. Hãy ghi lại.');
                    return;
                }
                const ext = commentAudioMimeToExt(usedMime);
                const file = new File([blob], `voice-${Date.now()}.${ext}`, {
                    type: blob.type || 'audio/webm',
                });
                handleCommentMediaSelected(form, file);
            };

            mediaRecorder.start(250);
            recordingStartedAt = Date.now();
            voiceBar.classList.remove('d-none');
            voiceBtn.classList.add('is-recording');

            recordingTimerId = setInterval(() => {
                const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
                if (voiceTimer) voiceTimer.textContent = formatCommentVoiceTimer(elapsed);
                if (elapsed >= COMMENT_VOICE_MAX_SECONDS) {
                    stopCommentVoice(true);
                }
            }, 250);
        }

        voiceBtn.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                stopCommentVoice(true);
            } else {
                startCommentVoice();
            }
        });
        if (voiceCancelBtn) {
            voiceCancelBtn.addEventListener('click', () => stopCommentVoice(false));
        }
        if (voiceSaveBtn) {
            voiceSaveBtn.addEventListener('click', () => stopCommentVoice(true));
        }
    }

    function commentActionsMenuHtml(comment, postId, username) {
        const editItem = comment.can_edit ? `
            <li>
                <button type="button" class="dropdown-item edit-comment-button"
                        data-comment-id="${comment.id}">
                    <i class="fas fa-pen me-2"></i>Chỉnh sửa
                </button>
            </li>` : '';
        const deleteItem = comment.can_delete ? `
            <li>
                <button type="button" class="dropdown-item text-danger delete-comment-button"
                        data-comment-id="${comment.id}">
                    <i class="fas fa-trash-alt me-2"></i>Xóa
                </button>
            </li>` : '';

        return `
            <div class="dropdown flex-shrink-0 comment-actions-menu">
                <button class="btn btn-link btn-sm p-0 text-muted" type="button"
                        data-bs-toggle="dropdown" aria-expanded="false" aria-label="Tùy chọn bình luận"
                        onclick="event.stopPropagation();">
                    <i class="fas fa-ellipsis-h"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li>
                        <button type="button" class="dropdown-item share-comment-button"
                                data-post-id="${postId}"
                                data-comment-id="${comment.id}">
                            <i class="fas fa-paper-plane me-2"></i>Chia sẻ qua chat
                        </button>
                    </li>
                    ${editItem}
                    ${deleteItem}
                </ul>
            </div>`;
    }

    function commentEditedLabelHtml(comment) {
        if (!comment.is_edited) return '';
        return '<span class="comment-edited-label text-muted ms-1">· Đã chỉnh sửa</span>';
    }

    function commentTextSpanHtml(text) {
        if (!text) return '';
        return `<div class="comment-text mt-1" data-raw-text="${escapeHtml(text)}">${formatCommentText(text)}</div>`;
    }

    function getCommentContentHost(commentEl) {
        return commentEl.querySelector('.comment-body-main')
            || commentEl.querySelector('.min-w-0.flex-grow-1')
            || commentEl.querySelector('.min-w-0')
            || commentEl;
    }

    function cancelCommentEdit(commentEl) {
        if (!commentEl) return;
        const editor = commentEl.querySelector('.comment-edit-form');
        if (editor) {
            if (typeof editor._stopEditVoice === 'function') {
                try { editor._stopEditVoice(false); } catch (_) { /* ignore */ }
            }
            const previewAudio = editor.querySelector('.comment-edit-preview-audio');
            if (previewAudio?.src?.startsWith('blob:')) {
                try { URL.revokeObjectURL(previewAudio.src); } catch (_) { /* ignore */ }
            }
            const previewVideo = editor.querySelector('.comment-edit-preview-video');
            if (previewVideo?.src?.startsWith('blob:')) {
                try { URL.revokeObjectURL(previewVideo.src); } catch (_) { /* ignore */ }
            }
            editor.remove();
        }
        commentEl.querySelectorAll('.comment-text, .comment-image-wrap, .comment-video-wrap, .comment-audio-wrap')
            .forEach((el) => el.classList.remove('d-none'));
        commentEl.classList.remove('is-editing-comment');
    }

    function applyCommentUpdateToDom(commentEl, comment) {
        const text = comment?.text || '';
        const isEdited = comment?.is_edited !== false;
        const host = getCommentContentHost(commentEl);
        let textEl = commentEl.querySelector('.comment-text');
        if (text) {
            if (!textEl) {
                const usernameLink = host.querySelector('a.text-decoration-none.fw-bold, a.fw-bold');
                textEl = document.createElement('div');
                textEl.className = 'comment-text mt-1';
                const header = host.querySelector('.comment-header-row');
                if (header) header.insertAdjacentElement('afterend', textEl);
                else if (usernameLink && usernameLink.parentNode === host) {
                    usernameLink.insertAdjacentElement('afterend', textEl);
                } else {
                    host.insertAdjacentElement('afterbegin', textEl);
                }
            }
            textEl.dataset.rawText = text;
            textEl.innerHTML = formatCommentText(text);
            textEl.classList.remove('d-none');
        } else if (textEl) {
            textEl.remove();
        }

        commentEl.querySelectorAll('.comment-image-wrap, .comment-video-wrap, .comment-audio-wrap')
            .forEach((el) => el.remove());
        const mediaHtml = commentMediaHtml(comment || {});
        if (mediaHtml) {
            const meta = host.querySelector('.comment-meta-row, .text-muted.small');
            const tmp = document.createElement('div');
            tmp.innerHTML = mediaHtml;
            Array.from(tmp.childNodes).forEach((node) => {
                if (meta) meta.insertAdjacentElement('beforebegin', node);
                else host.appendChild(node);
            });
        }

        const meta = commentEl.querySelector('.text-muted.small');
        if (meta && isEdited && !meta.querySelector('.comment-edited-label')) {
            const editedLabel = document.createElement('span');
            editedLabel.className = 'comment-edited-label text-muted ms-1';
            editedLabel.textContent = '· Đã chỉnh sửa';
            const firstSpan = meta.querySelector('span');
            if (firstSpan) firstSpan.insertAdjacentElement('afterend', editedLabel);
            else meta.insertAdjacentElement('afterbegin', editedLabel);
        }
    }

    function clearCommentEditPreview(form) {
        const preview = form.querySelector('.comment-edit-media-preview');
        const fileInput = form.querySelector('.comment-edit-file');
        if (fileInput) fileInput.value = '';
        form._pendingEditFile = null;
        if (!preview) return;
        preview.classList.add('d-none');
        const thumb = preview.querySelector('.comment-edit-preview-thumb');
        const videoEl = preview.querySelector('.comment-edit-preview-video');
        const audioEl = preview.querySelector('.comment-edit-preview-audio');
        const keepHint = preview.querySelector('.comment-edit-keep-hint');
        if (thumb) {
            thumb.src = '';
            thumb.classList.add('d-none');
        }
        if (videoEl) {
            videoEl.pause();
            if (videoEl.src?.startsWith('blob:')) {
                try { URL.revokeObjectURL(videoEl.src); } catch (_) { /* ignore */ }
            }
            videoEl.removeAttribute('src');
            videoEl.load();
            videoEl.classList.add('d-none');
        }
        if (audioEl) {
            audioEl.pause();
            if (audioEl.src?.startsWith('blob:')) {
                try { URL.revokeObjectURL(audioEl.src); } catch (_) { /* ignore */ }
            }
            audioEl.removeAttribute('src');
            audioEl.load();
            audioEl.classList.add('d-none');
        }
        if (keepHint) keepHint.classList.add('d-none');
    }

    async function setCommentEditMediaFile(form, file) {
        clearCommentEditPreview(form);
        if (!file) return false;

        const preview = form.querySelector('.comment-edit-media-preview');
        const thumb = preview?.querySelector('.comment-edit-preview-thumb');
        const videoEl = preview?.querySelector('.comment-edit-preview-video');
        const audioEl = preview?.querySelector('.comment-edit-preview-audio');
        if (!preview) return false;

        if (file.type.startsWith('image/')) {
            if (file.size > 5 * 1024 * 1024) {
                alert('Ảnh bình luận tối đa 5MB');
                return false;
            }
            form._pendingEditFile = file;
            const reader = new FileReader();
            reader.onload = (ev) => {
                if (thumb) {
                    thumb.src = ev.target.result;
                    thumb.classList.remove('d-none');
                }
                preview.classList.remove('d-none');
            };
            reader.readAsDataURL(file);
            return true;
        }

        if (isCommentAudioFile(file)) {
            if (file.size > COMMENT_AUDIO_MAX_BYTES) {
                alert('Ghi âm bình luận tối đa 10MB');
                return false;
            }
            form._pendingEditFile = file;
            if (audioEl) {
                audioEl.src = URL.createObjectURL(file);
                audioEl.classList.remove('d-none');
            }
            preview.classList.remove('d-none');
            return true;
        }

        if (file.type.startsWith('video/')) {
            if (file.size > COMMENT_VIDEO_MAX_BYTES) {
                alert('Video bình luận tối đa 15MB');
                return false;
            }
            try {
                const duration = await readVideoDuration(file);
                if (!Number.isFinite(duration) || duration > COMMENT_VIDEO_MAX_SECONDS + 0.35) {
                    alert('Video bình luận tối đa 5 giây');
                    return false;
                }
            } catch (err) {
                alert(err.message || 'Không đọc được video');
                return false;
            }
            form._pendingEditFile = file;
            if (videoEl) {
                videoEl.src = URL.createObjectURL(file);
                videoEl.classList.remove('d-none');
            }
            preview.classList.remove('d-none');
            return true;
        }

        alert('Chỉ chọn ảnh, video ngắn hoặc file ghi âm');
        return false;
    }

    function bindCommentEditMediaControls(form) {
        const fileInput = form.querySelector('.comment-edit-file');
        const voiceBtn = form.querySelector('.comment-edit-voice');
        const voiceBar = form.querySelector('.comment-edit-voice-bar');
        const voiceTimer = form.querySelector('.comment-edit-voice-timer');
        const voiceCancel = form.querySelector('.comment-edit-voice-cancel');
        const voiceSave = form.querySelector('.comment-edit-voice-save');
        const keepHint = form.querySelector('.comment-edit-keep-hint');

        if (form._hadExistingMedia && keepHint) {
            keepHint.classList.remove('d-none');
            form.querySelector('.comment-edit-media-preview')?.classList.remove('d-none');
        }

        if (fileInput) {
            fileInput.addEventListener('change', () => {
                const file = fileInput.files && fileInput.files[0];
                if (file) setCommentEditMediaFile(form, file);
            });
        }

        let mediaRecorder = null;
        let mediaStream = null;
        let recordedChunks = [];
        let recordingStartedAt = 0;
        let recordingTimerId = null;
        let shouldSaveVoice = false;

        function stopVoiceTracks() {
            if (mediaStream) {
                mediaStream.getTracks().forEach((t) => t.stop());
                mediaStream = null;
            }
        }

        function resetVoiceUI() {
            if (recordingTimerId) {
                clearInterval(recordingTimerId);
                recordingTimerId = null;
            }
            voiceBar?.classList.add('d-none');
            if (voiceTimer) voiceTimer.textContent = '0:00';
            voiceBtn?.classList.remove('is-recording');
            recordedChunks = [];
            mediaRecorder = null;
            shouldSaveVoice = false;
        }

        function stopEditVoice(save) {
            shouldSaveVoice = !!save;
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                try { mediaRecorder.stop(); } catch (_) { /* ignore */ }
            } else {
                stopVoiceTracks();
                resetVoiceUI();
            }
        }
        form._stopEditVoice = stopEditVoice;

        async function startEditVoice() {
            if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
                alert('Trình duyệt không hỗ trợ ghi âm.');
                return;
            }
            if (mediaRecorder && mediaRecorder.state === 'recording') return;
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err) {
                alert('Không thể truy cập micro. Hãy cho phép quyền micro rồi thử lại.');
                return;
            }
            recordedChunks = [];
            shouldSaveVoice = false;
            const mime = pickCommentAudioMimeType();
            try {
                mediaRecorder = mime
                    ? new MediaRecorder(mediaStream, { mimeType: mime })
                    : new MediaRecorder(mediaStream);
            } catch (err) {
                stopVoiceTracks();
                alert('Không thể bắt đầu ghi âm trên trình duyệt này.');
                return;
            }
            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) recordedChunks.push(e.data);
            };
            mediaRecorder.onstop = () => {
                stopVoiceTracks();
                const save = shouldSaveVoice;
                const chunks = recordedChunks.slice();
                const usedMime = (mediaRecorder && mediaRecorder.mimeType) || mime || 'audio/webm';
                resetVoiceUI();
                if (!save) return;
                const blob = new Blob(chunks, { type: usedMime.split(';')[0] });
                if (blob.size < 500) {
                    alert('Bản ghi quá ngắn. Hãy ghi lại.');
                    return;
                }
                const ext = commentAudioMimeToExt(usedMime);
                const file = new File([blob], `voice-${Date.now()}.${ext}`, {
                    type: blob.type || 'audio/webm',
                });
                setCommentEditMediaFile(form, file);
            };
            mediaRecorder.start(250);
            recordingStartedAt = Date.now();
            voiceBar?.classList.remove('d-none');
            voiceBtn?.classList.add('is-recording');
            recordingTimerId = setInterval(() => {
                const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
                if (voiceTimer) voiceTimer.textContent = formatCommentVoiceTimer(elapsed);
                if (elapsed >= COMMENT_VOICE_MAX_SECONDS) stopEditVoice(true);
            }, 250);
        }

        if (voiceBtn) {
            voiceBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (mediaRecorder && mediaRecorder.state === 'recording') stopEditVoice(true);
                else startEditVoice();
            });
        }
        voiceCancel?.addEventListener('click', (e) => {
            e.preventDefault();
            stopEditVoice(false);
        });
        voiceSave?.addEventListener('click', (e) => {
            e.preventDefault();
            stopEditVoice(true);
        });
    }

    function startCommentEdit(commentId) {
        const commentEl = document.getElementById(`comment-${commentId}`);
        if (!commentEl || commentEl.classList.contains('is-editing-comment')) return;

        document.querySelectorAll('.is-editing-comment').forEach((el) => cancelCommentEdit(el));

        const textEl = commentEl.querySelector('.comment-text');
        const currentText = textEl?.dataset?.rawText != null
            ? textEl.dataset.rawText
            : (textEl?.textContent || '');
        const existingMedia = commentEl.querySelector('.comment-image-wrap, .comment-video-wrap, .comment-audio-wrap');

        const host = getCommentContentHost(commentEl);
        commentEl.classList.add('is-editing-comment');
        if (textEl) textEl.classList.add('d-none');
        if (existingMedia) existingMedia.classList.add('d-none');

        const form = document.createElement('div');
        form.className = 'comment-edit-form mt-1 mb-1';
        form._hadExistingMedia = !!existingMedia;
        form._pendingEditFile = null;
        form.innerHTML = `
            <textarea class="form-control form-control-sm comment-edit-input" rows="2" maxlength="500">${escapeHtml(currentText)}</textarea>
            <div class="comment-edit-media-preview d-none mt-2">
                <div class="comment-edit-preview-inner">
                    <img src="" alt="Xem trước" class="comment-edit-preview-thumb d-none">
                    <video src="" class="comment-edit-preview-video d-none" muted playsinline controls></video>
                    <audio src="" class="comment-edit-preview-audio d-none" controls></audio>
                </div>
                <small class="text-muted d-block mt-1 comment-edit-keep-hint d-none">Giữ media hiện tại (đổi bằng nút bên dưới)</small>
            </div>
            <div class="comment-edit-voice-bar d-none mt-2">
                <span class="comment-voice-rec-dot" aria-hidden="true"></span>
                <span class="comment-edit-voice-timer">0:00</span>
                <span class="comment-voice-hint">Đang ghi âm...</span>
                <div class="ms-auto d-flex gap-1">
                    <button type="button" class="btn btn-sm btn-light comment-edit-voice-cancel">Hủy</button>
                    <button type="button" class="btn btn-sm btn-primary comment-edit-voice-save">Dùng</button>
                </div>
            </div>
            <div class="d-flex gap-1 align-items-center mt-2 flex-wrap">
                <label class="btn btn-sm btn-light mb-0" title="Đổi ảnh/video">
                    <i class="far fa-image"></i>
                    <input type="file" class="d-none comment-edit-file" accept="image/*,video/mp4,video/webm,video/quicktime,audio/*">
                </label>
                <button type="button" class="btn btn-sm btn-light comment-edit-voice" title="Ghi âm mới">
                    <i class="fas fa-microphone"></i>
                </button>
            </div>
            <div class="d-flex gap-2 mt-2">
                <button type="button" class="btn btn-sm btn-primary comment-edit-save">Lưu</button>
                <button type="button" class="btn btn-sm btn-light comment-edit-cancel">Hủy</button>
            </div>`;

        const mediaEl = existingMedia;
        if (mediaEl) mediaEl.insertAdjacentElement('beforebegin', form);
        else {
            const meta = host.querySelector('.text-muted.small');
            if (meta) meta.insertAdjacentElement('beforebegin', form);
            else host.appendChild(form);
        }

        bindCommentEditMediaControls(form);

        const textarea = form.querySelector('.comment-edit-input');
        if (typeof window.initCommentMentionSuggestions === 'function') {
            // Cho phép bind lại mỗi lần mở form sửa
            if (textarea) delete textarea.dataset.captionSuggestBound;
            window.initCommentMentionSuggestions(textarea, { placement: 'below' });
        }
        textarea?.focus();
        textarea?.setSelectionRange(textarea.value.length, textarea.value.length);

        form.querySelector('.comment-edit-cancel')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            cancelCommentEdit(commentEl);
        });
        form.querySelector('.comment-edit-save')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            saveCommentEdit(commentId, commentEl, form);
        });
    }

    function saveCommentEdit(commentId, commentEl, form) {
        const saveBtn = form.querySelector('.comment-edit-save');
        const cancelBtn = form.querySelector('.comment-edit-cancel');
        const textarea = form.querySelector('.comment-edit-input');
        const text = (textarea?.value || '').trim();
        const pendingFile = form._pendingEditFile || null;
        const hadMedia = !!form._hadExistingMedia;

        if (!text && !pendingFile && !hadMedia) {
            alert('Bình luận không được để trống');
            return;
        }

        if (saveBtn) saveBtn.disabled = true;
        if (cancelBtn) cancelBtn.disabled = true;

        const formData = new FormData();
        formData.append('text', text);
        if (pendingFile) {
            if (isCommentAudioFile(pendingFile)) formData.append('audio', pendingFile);
            else if (pendingFile.type.startsWith('video/')) formData.append('video', pendingFile);
            else formData.append('image', pendingFile);
        }

        fetch(`/api/posts/comments/${commentId}/edit/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: formData,
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Không lưu được bình luận');
            return data;
        })
        .then((data) => {
            cancelCommentEdit(commentEl);
            applyCommentUpdateToDom(commentEl, data.comment || { text, is_edited: true });
            if (typeof window.initHoshiAudioPlayers === 'function') {
                window.initHoshiAudioPlayers(commentEl);
            }
        })
        .catch((err) => {
            console.error('Edit comment error:', err);
            alert(err.message || 'Không lưu được bình luận');
            if (saveBtn) saveBtn.disabled = false;
            if (cancelBtn) cancelBtn.disabled = false;
        });
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
            <div class="comment-body-main">
                <div class="d-flex justify-content-between align-items-start gap-2 comment-header-row">
                    <a href="${profileUrl(username)}" class="text-dark text-decoration-none fw-bold">${escapeHtml(username)}</a>
                    ${commentActionsMenuHtml(comment, postId, username)}
                </div>
                ${commentTextSpanHtml(comment.text)}
                ${commentMediaHtml(comment)}
                <div class="text-muted small d-flex align-items-center flex-wrap mt-1 comment-meta-row">
                    <span>${timeLabel}</span>${commentEditedLabelHtml(comment)}
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
                <div class="comment-body-main">
                    <div class="d-flex justify-content-between align-items-start gap-2 comment-header-row">
                        <a href="${profileUrl(username)}" class="text-dark text-decoration-none fw-bold">${escapeHtml(username)}</a>
                        ${commentActionsMenuHtml(comment, postId, username)}
                    </div>
                    ${commentTextSpanHtml(comment.text)}
                    ${commentMediaHtml(comment)}
                    <div class="text-muted small d-flex align-items-center flex-wrap mt-1 comment-meta-row">
                        <span>${timeLabel}</span>${commentEditedLabelHtml(comment)}
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

    function updateFeedCommentCount(postId, delta = 1) {
        const postCard = document.getElementById(`post-${postId}`);
        const countEl = postCard?.querySelector(`a[href="/posts/${postId}/"] span`);
        if (countEl) {
            const current = parseInt(countEl.textContent, 10) || 0;
            countEl.textContent = Math.max(0, current + delta);
        }
    }

    function deleteComment(commentId, button) {
        if (!commentId || commentId === 'undefined') {
            alert('Không thể xóa bình luận. Vui lòng tải lại trang và thử lại.');
            return;
        }
        if (!confirm('Bạn có chắc chắn muốn xóa bình luận này?')) return;

        if (button) button.disabled = true;

        fetch(`/api/posts/comments/${commentId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        })
        .then(async (response) => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Không xóa được bình luận');
            return data;
        })
        .then((data) => {
            if (!data.success) throw new Error(data.error || 'Không xóa được bình luận');

            const commentEl = document.getElementById(`comment-${commentId}`);
            if (!commentEl) return;

            const postCard = commentEl.closest('[id^="post-"]');
            const postId = postCard?.id?.replace('post-', '');
            const isRoot = commentEl.classList.contains('root-comment');
            let removedCount = 1;

            if (isRoot) {
                removedCount += commentEl.querySelectorAll('.reply-comment').length;
                commentEl.remove();
            } else {
                const repliesBox = commentEl.closest('.comment-replies');
                const block = commentEl.closest('.comment-replies-block');
                commentEl.remove();
                if (repliesBox && repliesBox.children.length === 0) {
                    block?.remove();
                }
            }

            if (postId) {
                if (typeof data.comments_count === 'number') {
                    const countEl = postCard?.querySelector(`a[href="/posts/${postId}/"] span`);
                    if (countEl) countEl.textContent = data.comments_count;
                } else {
                    updateFeedCommentCount(postId, -removedCount);
                }
            }
        })
        .catch((err) => {
            console.error('Delete comment error:', err);
            alert(err.message || 'Có lỗi xảy ra khi xóa bình luận.');
            if (button) button.disabled = false;
        });
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

    function addComment(postId, text, parentId, form, mediaFile) {
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
        if (mediaFile) {
            if (isCommentAudioFile(mediaFile)) formData.append('audio', mediaFile);
            else if (mediaFile.type.startsWith('video/')) formData.append('video', mediaFile);
            else formData.append('image', mediaFile);
        }

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
                clearCommentMediaPreview(form);
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

        if (typeof window.initHoshiAudioPlayers === 'function') {
            window.initHoshiAudioPlayers(scope);
        }

        scope.querySelectorAll('.carousel:not([data-initialized])').forEach((carousel) => {
            try {
                const hasAudio = !!carousel.querySelector('.post-audio-player, audio.post-audio');
                new bootstrap.Carousel(carousel, {
                    interval: false,
                    touch: hasAudio ? false : true,
                });
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

            bindCommentVoiceRecording(form);

            if (imageInput && preview && !imageInput.dataset.previewBound) {
                imageInput.dataset.previewBound = '1';
                imageInput.addEventListener('change', () => {
                    const file = imageInput.files && imageInput.files[0];
                    if (!file) {
                        clearCommentMediaPreview(form);
                        return;
                    }
                    handleCommentMediaSelected(form, file);
                });
                if (clearBtn) {
                    clearBtn.addEventListener('click', () => clearCommentMediaPreview(form));
                }
            }

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const postId = form.getAttribute('data-post-id');
                const input = document.getElementById(`comment-input-${postId}`);
                const text = input?.value.trim() || '';
                const mediaFile = form._pendingCommentMedia
                    || (imageInput && imageInput.files && imageInput.files[0] ? imageInput.files[0] : null);
                if (!text && !mediaFile) return;
                if (mediaFile && mediaFile.type.startsWith('video/') && !isCommentAudioFile(mediaFile)) {
                    try {
                        const duration = await readVideoDuration(mediaFile);
                        if (!Number.isFinite(duration) || duration > COMMENT_VIDEO_MAX_SECONDS + 0.35) {
                            alert('Video bình luận tối đa 5 giây');
                            return;
                        }
                    } catch (err) {
                        alert(err.message || 'Không đọc được video');
                        return;
                    }
                }
                const replyInfo = form.querySelector('.reply-info');
                const parentId = replyInfo && !replyInfo.classList.contains('d-none')
                    ? replyInfo.getAttribute('data-parent-id') : null;
                addComment(postId, text, parentId, form, mediaFile);
            });

            const commentInput = form.querySelector('.comment-input, input[name="text"]');
            if (typeof window.initCommentMentionSuggestions === 'function') {
                window.initCommentMentionSuggestions(commentInput);
            }

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

        scope.querySelectorAll('.delete-comment-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                deleteComment(button.getAttribute('data-comment-id'), button);
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.edit-comment-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                startCommentEdit(button.getAttribute('data-comment-id'));
            });
            button.setAttribute('data-initialized', 'true');
        });

        scope.querySelectorAll('.share-comment-button:not([data-initialized])').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const postId = button.getAttribute('data-post-id');
                const commentId = button.getAttribute('data-comment-id');
                if (typeof window.openShareCommentModal === 'function') {
                    window.openShareCommentModal(postId, commentId);
                } else {
                    alert('Không tải được chức năng chia sẻ.');
                }
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
            markPostsSeen(newPosts.map((p) => p.id));

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
        if (feedType === 'diverse') {
            feedSeed = createFeedSeed();
        }

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
