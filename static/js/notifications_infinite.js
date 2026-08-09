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

    function createNotificationElement(n) {
        const unreadClass = n.is_read ? '' : 'bg-light';
        const username = escapeHtml(n.sender?.username || '');
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
            el.dataset.username = n.sender?.username || '';
            el.innerHTML = `
                <div class="d-flex w-100 justify-content-between align-items-center gap-2 flex-wrap">
                    <div class="d-flex align-items-center">
                        <a href="${link}" class="text-decoration-none text-dark">
                            <img src="${avatar}" class="rounded-circle me-2" width="40" height="40" alt="${username}">
                        </a>
                        <div>
                            <a href="${link}" class="text-decoration-none text-dark">
                                <strong>${username}</strong>
                            </a>
                            ${text}
                            <div><small class="text-muted">${timeAgo} trước</small></div>
                        </div>
                    </div>
                    <div class="d-flex gap-2 follow-request-actions">
                        <button type="button" class="btn btn-sm btn-primary accept-follow-request" data-username="${username}">Xác nhận</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary reject-follow-request" data-username="${username}">Từ chối</button>
                    </div>
                </div>
            `;
            return el;
        }

        const el = document.createElement('a');
        el.href = link;
        el.className = `list-group-item list-group-item-action text-decoration-none text-dark ${unreadClass}`;
        el.id = `notification-${n.id}`;
        el.dataset.id = n.id;
        el.dataset.type = n.notification_type || '';
        el.innerHTML = `
            <div class="d-flex w-100 justify-content-between gap-2">
                <div class="d-flex align-items-start">
                    <img src="${avatar}" class="rounded-circle me-2" width="40" height="40" alt="${username}">
                    <div>
                        <strong>${username}</strong>
                        ${text}
                    </div>
                </div>
                <small class="text-muted text-nowrap">${timeAgo} trước</small>
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

    list.addEventListener('click', (e) => {
        if (e.target.closest('.accept-follow-request, .reject-follow-request')) return;
        const item = e.target.closest('[data-id]');
        if (!item || item.dataset.type === 'follow_request') return;
        const id = item.dataset.id;
        if (!id) return;
        fetch(`/notifications/mark-as-read/${id}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1]
                    ? decodeURIComponent(document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)[1])
                    : '',
            },
            credentials: 'same-origin',
            keepalive: true,
        }).then(() => item.classList.remove('bg-light')).catch(() => {});
    });
})();
