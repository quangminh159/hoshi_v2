/**
 * Cuộn vô hạn + filter pills trang Thông báo
 */
(function () {
    'use strict';

    const list = document.getElementById('notifications-list');
    const sentinel = document.getElementById('notifications-sentinel');
    const loadingEl = document.getElementById('notifications-loading');
    const endEl = document.getElementById('notifications-end');
    const filtersEl = document.querySelector('.notif-filters');
    if (!list || !sentinel) return;

    const apiUrl = list.dataset.apiUrl || '/notifications/api/';
    let activeFilter = list.dataset.filter || 'all';
    let nextPage = list.dataset.nextPage ? parseInt(list.dataset.nextPage, 10) : null;
    let hasMore = list.dataset.hasMore === 'true';
    let isLoading = false;
    const loadedIds = new Set(
        Array.from(list.querySelectorAll('[data-id]')).map((el) => String(el.dataset.id))
    );

    window.notificationsInfiniteRegister = function (id) {
        if (id != null) loadedIds.add(String(id));
    };

    function escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function csrfToken() {
        const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    function deleteBtnHtml(id) {
        return `
            <button type="button"
                    class="btn btn-sm btn-link text-muted delete-notification-btn flex-shrink-0"
                    data-id="${id}"
                    title="Xóa thông báo"
                    aria-label="Xóa thông báo">
                <i class="fas fa-trash-alt" aria-hidden="true"></i>
            </button>`;
    }

    function followBackActionHtml(n, rawUsername) {
        const safeUser = escapeHtml(rawUsername);
        if (n.show_follow_back) {
            return `<button type="button" class="btn btn-sm btn-primary follow-back-btn flex-shrink-0" data-username="${safeUser}">Theo dõi lại</button>`;
        }
        if (n.follow_request_pending) {
            return '<button type="button" class="btn btn-sm btn-outline-secondary flex-shrink-0" disabled>Đã gửi yêu cầu</button>';
        }
        if (n.is_following_sender) {
            return '<button type="button" class="btn btn-sm btn-outline-secondary flex-shrink-0" disabled>Đang theo dõi</button>';
        }
        return '';
    }

    function createNotificationElement(n) {
        const unreadClass = n.is_read ? '' : 'bg-light';
        const username = escapeHtml(n.sender?.username || '');
        const rawUsername = n.sender?.username || '';
        const avatar = escapeHtml(n.sender?.avatar_url || '/static/img/default-avatar.png');
        const text = escapeHtml(n.text || '');
        const timeAgo = escapeHtml(n.time_ago || '');
        const link = escapeHtml(n.link || '#');

        if (n.notification_type === 'follow_request') {
            const el = document.createElement('div');
            el.className = `list-group-item ${unreadClass}`;
            el.id = `notification-${n.id}`;
            el.dataset.id = n.id;
            el.dataset.type = 'follow_request';
            el.dataset.username = rawUsername;
            el.innerHTML = `
                <div class="d-flex w-100 justify-content-between align-items-center gap-2 flex-wrap">
                    <div class="d-flex align-items-center min-w-0">
                        <a href="${link}" class="text-decoration-none text-dark">
                            <img src="${avatar}" class="rounded-circle me-2" width="40" height="40" alt="${username}">
                        </a>
                        <div class="min-w-0">
                            <a href="${link}" class="text-decoration-none text-dark">
                                <strong>${username}</strong>
                            </a>
                            ${text}
                            <div><small class="text-muted">${timeAgo} trước</small></div>
                        </div>
                    </div>
                    <div class="d-flex gap-2 align-items-center flex-shrink-0">
                        <button type="button" class="btn btn-sm btn-primary accept-follow-request" data-username="${username}">Xác nhận</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary reject-follow-request" data-username="${username}">Từ chối</button>
                        ${deleteBtnHtml(n.id)}
                    </div>
                </div>
            `;
            return el;
        }

        if (n.notification_type === 'follow') {
            const el = document.createElement('div');
            el.className = `list-group-item ${unreadClass}`;
            el.id = `notification-${n.id}`;
            el.dataset.id = n.id;
            el.dataset.type = 'follow';
            el.dataset.username = rawUsername;
            el.innerHTML = `
                <div class="d-flex w-100 justify-content-between align-items-center gap-2">
                    <a href="${link}" class="d-flex align-items-center min-w-0 text-decoration-none text-dark flex-grow-1">
                        <img src="${avatar}" class="rounded-circle me-2 flex-shrink-0" width="40" height="40" alt="${username}">
                        <div class="min-w-0">
                            <strong>${username}</strong>
                            ${text}
                            <div><small class="text-muted">${timeAgo} trước</small></div>
                        </div>
                    </a>
                    <div class="d-flex gap-2 align-items-center flex-shrink-0">
                        ${followBackActionHtml(n, rawUsername)}
                        ${deleteBtnHtml(n.id)}
                    </div>
                </div>
            `;
            return el;
        }

        const el = document.createElement('div');
        el.className = `list-group-item ${unreadClass}`;
        el.id = `notification-${n.id}`;
        el.dataset.id = n.id;
        el.dataset.type = n.notification_type || '';
        el.innerHTML = `
            <div class="d-flex w-100 justify-content-between align-items-center gap-2">
                <a href="${link}" class="d-flex align-items-start min-w-0 text-decoration-none text-dark flex-grow-1">
                    <img src="${avatar}" class="rounded-circle me-2 flex-shrink-0" width="40" height="40" alt="${username}">
                    <div class="min-w-0">
                        <strong>${username}</strong>
                        ${text}
                        <div><small class="text-muted">${timeAgo} trước</small></div>
                    </div>
                </a>
                ${deleteBtnHtml(n.id)}
            </div>
        `;
        return el;
    }

    function setLoading(on) {
        isLoading = on;
        loadingEl?.classList.toggle('d-none', !on);
    }

    function showEmpty() {
        if (list.querySelector('[data-id]')) return;
        if (document.getElementById('notifications-empty')) return;
        const empty = document.createElement('div');
        empty.className = 'alert alert-info mb-0';
        empty.id = 'notifications-empty';
        empty.textContent = 'Bạn không có thông báo nào.';
        list.appendChild(empty);
        syncHeaderActions();
    }

    function syncHeaderActions() {
        const actions = document.getElementById('notif-header-actions');
        if (!actions) return;
        const hasItems = !!list.querySelector('[data-id]');
        actions.classList.toggle('d-none', !hasItems);
    }

    function buildUrl(page) {
        const url = new URL(apiUrl, window.location.origin);
        url.searchParams.set('page', String(page));
        url.searchParams.set('filter', activeFilter || 'all');
        return url.toString();
    }

    async function loadMore() {
        if (isLoading || !hasMore || !nextPage) return;
        setLoading(true);

        try {
            const response = await fetch(buildUrl(nextPage), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const items = Array.isArray(data.notifications) ? data.notifications : [];

            document.getElementById('notifications-empty')?.remove();

            items.forEach((n) => {
                if (!n?.id || loadedIds.has(String(n.id))) return;
                loadedIds.add(String(n.id));
                list.appendChild(createNotificationElement(n));
            });

            hasMore = data.has_next === true;
            nextPage = data.next_page || null;
            list.dataset.hasMore = hasMore ? 'true' : 'false';
            list.dataset.nextPage = nextPage || '';
            syncHeaderActions();

            if (!hasMore) {
                endEl?.classList.remove('d-none');
                loadingEl?.classList.add('d-none');
                if (!list.querySelector('[data-id]')) showEmpty();
            }
        } catch (err) {
            console.error('Notifications load error:', err);
        } finally {
            setLoading(false);
        }
    }

    async function switchFilter(filterKey) {
        if (!filterKey || filterKey === activeFilter) return;
        activeFilter = filterKey;
        list.dataset.filter = filterKey;

        filtersEl?.querySelectorAll('.notif-filter-pill').forEach((btn) => {
            const on = btn.dataset.filter === filterKey;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });

        const url = new URL(window.location.href);
        if (filterKey === 'all') url.searchParams.delete('filter');
        else url.searchParams.set('filter', filterKey);
        window.history.replaceState({}, '', url);

        loadedIds.clear();
        list.innerHTML = '';
        endEl?.classList.add('d-none');
        hasMore = true;
        nextPage = 1;
        observer.disconnect();
        setLoading(true);

        try {
            const response = await fetch(buildUrl(1), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const items = Array.isArray(data.notifications) ? data.notifications : [];

            items.forEach((n) => {
                if (!n?.id || loadedIds.has(String(n.id))) return;
                loadedIds.add(String(n.id));
                list.appendChild(createNotificationElement(n));
            });

            hasMore = data.has_next === true;
            nextPage = data.next_page || null;
            list.dataset.hasMore = hasMore ? 'true' : 'false';
            list.dataset.nextPage = nextPage || '';
            syncHeaderActions();

            if (!items.length) showEmpty();
            if (hasMore) observer.observe(sentinel);
            else {
                endEl?.classList.toggle('d-none', !items.length);
                loadingEl?.classList.add('d-none');
            }
        } catch (err) {
            console.error('Notifications filter error:', err);
            showEmpty();
        } finally {
            setLoading(false);
        }
    }

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadMore();
        }
    }, { rootMargin: '400px', threshold: 0 });

    if (hasMore) {
        observer.observe(sentinel);
    } else if (loadedIds.size > 0) {
        endEl?.classList.remove('d-none');
        loadingEl?.classList.add('d-none');
    }

    filtersEl?.addEventListener('click', (e) => {
        const btn = e.target.closest('.notif-filter-pill');
        if (!btn) return;
        e.preventDefault();
        switchFilter(btn.dataset.filter || 'all');
    });

    document.getElementById('mark-all-read-btn')?.addEventListener('click', (e) => {
        e.preventDefault();
        const btn = e.currentTarget;
        if (btn.disabled) return;
        btn.disabled = true;
        const body = new URLSearchParams();
        body.set('filter', activeFilter || 'all');
        fetch('/notifications/mark-all-as-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
            body: body.toString(),
        })
            .then(async (resp) => {
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok) throw new Error(data.error || 'Lỗi');
                list.querySelectorAll('[data-id]').forEach((el) => el.classList.remove('bg-light'));
            })
            .catch((err) => {
                console.error(err);
                window.alert(err.message || 'Không thể đánh dấu đã đọc.');
            })
            .finally(() => {
                btn.disabled = false;
            });
    });

    document.getElementById('delete-all-notifications-btn')?.addEventListener('click', (e) => {
        e.preventDefault();
        const btn = e.currentTarget;
        if (btn.disabled) return;

        const scopeLabel = activeFilter && activeFilter !== 'all'
            ? 'các thông báo trong bộ lọc hiện tại'
            : 'tất cả thông báo';
        if (!window.confirm(`Xóa ${scopeLabel}? Hành động này không hoàn tác.`)) return;

        btn.disabled = true;
        const body = new URLSearchParams();
        body.set('filter', activeFilter || 'all');
        fetch('/notifications/delete-all/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
            body: body.toString(),
        })
            .then(async (resp) => {
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok) throw new Error(data.error || 'Xóa thất bại');
                loadedIds.clear();
                list.innerHTML = '';
                hasMore = false;
                nextPage = null;
                list.dataset.hasMore = 'false';
                list.dataset.nextPage = '';
                endEl?.classList.add('d-none');
                loadingEl?.classList.add('d-none');
                showEmpty();
            })
            .catch((err) => {
                console.error(err);
                window.alert(err.message || 'Không thể xóa thông báo.');
            })
            .finally(() => {
                btn.disabled = false;
            });
    });

    syncHeaderActions();

    list.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.delete-notification-btn');
        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const id = deleteBtn.getAttribute('data-id');
            if (!id || deleteBtn.disabled) return;
            if (!window.confirm('Xóa thông báo này?')) return;
            deleteBtn.disabled = true;

            fetch(`/notifications/${encodeURIComponent(id)}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
                .then(async (resp) => {
                    const data = await resp.json().catch(() => ({}));
                    if (!resp.ok) throw new Error(data.error || 'Xóa thất bại');
                    const item = document.getElementById(`notification-${id}`)
                        || deleteBtn.closest('[data-id]');
                    item?.remove();
                    loadedIds.delete(String(id));
                    if (!list.querySelector('[data-id]')) showEmpty();
                    else syncHeaderActions();
                })
                .catch((err) => {
                    console.error('Delete notification error:', err);
                    deleteBtn.disabled = false;
                    window.alert(err.message || 'Không thể xóa thông báo.');
                });
            return;
        }

        const followBackBtn = e.target.closest('.follow-back-btn');
        if (followBackBtn) {
            e.preventDefault();
            e.stopPropagation();
            const username = followBackBtn.getAttribute('data-username');
            if (!username || followBackBtn.disabled) return;
            followBackBtn.disabled = true;
            const prevLabel = followBackBtn.textContent;
            followBackBtn.textContent = '...';

            fetch(`/api/accounts/follow/${encodeURIComponent(username)}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
                .then(async (resp) => {
                    const data = await resp.json().catch(() => ({}));
                    if (!resp.ok && data.status !== 'already_following') {
                        throw new Error(data.error || 'follow failed');
                    }
                    const status = data.status || (resp.ok ? 'following' : '');
                    const replacement = document.createElement('button');
                    replacement.type = 'button';
                    replacement.className = 'btn btn-sm btn-outline-secondary flex-shrink-0';
                    replacement.disabled = true;
                    if (status === 'requested' || status === 'already_requested') {
                        replacement.textContent = 'Đã gửi yêu cầu';
                    } else {
                        replacement.textContent = 'Đang theo dõi';
                    }
                    followBackBtn.replaceWith(replacement);

                    list.querySelectorAll('.follow-back-btn').forEach((btn) => {
                        if (btn.getAttribute('data-username') !== username) return;
                        const clone = replacement.cloneNode(true);
                        btn.replaceWith(clone);
                    });
                })
                .catch((err) => {
                    console.error('Follow back error:', err);
                    followBackBtn.disabled = false;
                    followBackBtn.textContent = prevLabel;
                    window.alert(err.message || 'Không thể theo dõi lại.');
                });
            return;
        }

        if (e.target.closest('.accept-follow-request, .reject-follow-request')) return;
        const item = e.target.closest('[data-id]');
        if (!item || item.dataset.type === 'follow_request') return;
        if (item.dataset.type === 'follow' && !e.target.closest('a')) return;
        const id = item.dataset.id;
        if (!id) return;
        fetch(`/notifications/mark-as-read/${id}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
            },
            credentials: 'same-origin',
            keepalive: true,
        }).then(() => item.classList.remove('bg-light')).catch(() => {});
    });
})();
