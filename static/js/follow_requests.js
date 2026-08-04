/**
 * Accept / reject private-account follow requests.
 */
(function () {
    'use strict';

    function csrfToken() {
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function postJson(url) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        }).then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || 'Không thể xử lý yêu cầu theo dõi');
            }
            return data;
        });
    }

    function markActionsDone(container, label) {
        if (!container) return;
        container.innerHTML = `<span class="text-muted small">${label}</span>`;
    }

    function handleAccept(button) {
        const username = button.dataset.username;
        if (!username) return;
        const row = button.closest('[data-type="follow_request"], .notification-item, .list-group-item');
        const actions = row?.querySelector('.follow-request-actions') || button.parentElement;
        button.disabled = true;
        postJson(`/api/accounts/follow-requests/${encodeURIComponent(username)}/accept/`)
            .then(() => {
                markActionsDone(actions, 'Đã xác nhận');
                if (row?.dataset?.id) {
                    fetch(`/notifications/mark-as-read/${row.dataset.id}/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrfToken() },
                    }).catch(() => {});
                }
            })
            .catch((err) => {
                button.disabled = false;
                alert(err.message);
            });
    }

    function handleReject(button) {
        const username = button.dataset.username;
        if (!username) return;
        const row = button.closest('[data-type="follow_request"], .notification-item, .list-group-item');
        const actions = row?.querySelector('.follow-request-actions') || button.parentElement;
        button.disabled = true;
        postJson(`/api/accounts/follow-requests/${encodeURIComponent(username)}/reject/`)
            .then(() => {
                markActionsDone(actions, 'Đã từ chối');
                if (row) {
                    setTimeout(() => row.remove(), 400);
                }
            })
            .catch((err) => {
                button.disabled = false;
                alert(err.message);
            });
    }

    document.addEventListener('click', (event) => {
        const acceptBtn = event.target.closest('.accept-follow-request');
        if (acceptBtn) {
            event.preventDefault();
            event.stopPropagation();
            handleAccept(acceptBtn);
            return;
        }
        const rejectBtn = event.target.closest('.reject-follow-request');
        if (rejectBtn) {
            event.preventDefault();
            event.stopPropagation();
            handleReject(rejectBtn);
        }
    });

    window.renderFollowRequestActions = function (username) {
        return `
            <div class="d-flex gap-2 follow-request-actions mt-2">
                <button type="button" class="btn btn-sm btn-primary accept-follow-request" data-username="${username}">Xác nhận</button>
                <button type="button" class="btn btn-sm btn-outline-secondary reject-follow-request" data-username="${username}">Từ chối</button>
            </div>
        `;
    };
})();
