/**
 * Modal chia sẻ bài viết 
 * chia sẻ bình luận qua chat 
 */
(function () {
    function getCsrfToken(modal) {
        return modal.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || (typeof getCookie === 'function' ? getCookie('csrftoken') : '');
    }

    function setButtonLoading(button, loading) {
        if (!button) return;
        const text = button.querySelector('.btn-text');
        const spinner = button.querySelector('.spinner-border');
        button.disabled = loading;
        if (text) text.classList.toggle('d-none', loading);
        if (spinner) spinner.classList.toggle('d-none', !loading);
    }

    function isCommentMode(modal) {
        return Boolean(modal.querySelector('.share-comment-id')?.value);
    }

    function setCommentMode(modal, enabled) {
        const title = modal.querySelector('.modal-title');
        const tabs = modal.querySelector('.share-post-tabs');
        const feedPane = modal.querySelector('.share-tab-pane--feed');
        const dmPlaceholder = modal.querySelector('.share-dm-message');

        modal.classList.toggle('share-comment-mode', enabled);

        if (title) {
            title.textContent = enabled ? 'Chia sẻ bình luận' : 'Chia sẻ bài viết';
        }
        if (tabs) tabs.classList.toggle('d-none', enabled);
        if (feedPane) feedPane.classList.toggle('d-none', enabled);
        if (dmPlaceholder) {
            dmPlaceholder.placeholder = enabled
                ? 'Viết tin nhắn kèm theo bình luận...'
                : 'Viết tin nhắn kèm theo...';
        }
    }

    function resetCommentMode(modal) {
        const commentInput = modal.querySelector('.share-comment-id');
        if (commentInput) commentInput.value = '';
        setCommentMode(modal, false);
    }

    function switchShareTab(modal, tabName) {
        const suffix = modal.dataset.modalSuffix || '';
        const feedPane = modal.querySelector(`#share-tab-feed${suffix}`);
        const messagePane = modal.querySelector(`#share-tab-message${suffix}`);
        const feedBtn = modal.querySelector('.share-feed-submit');
        const dmBtn = modal.querySelector('.share-dm-submit');

        modal.querySelectorAll('.share-tab-btn').forEach((btn) => {
            const active = btn.dataset.shareTab === tabName;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        if (feedPane) feedPane.classList.toggle('d-none', tabName !== `feed${suffix}`);
        if (messagePane) messagePane.classList.toggle('d-none', tabName !== `message${suffix}`);
        if (feedBtn) feedBtn.classList.toggle('d-none', tabName !== `feed${suffix}`);
        if (dmBtn) dmBtn.classList.toggle('d-none', tabName !== `message${suffix}`);

        if (tabName === `message${suffix}`) {
            loadRecipients(modal);
        }
    }

    function renderRecipients(modal, recipients, query) {
        const listEl = modal.querySelector('.share-recipients-list');
        if (!listEl) return;

        const q = (query || '').trim().toLowerCase();
        const filtered = q
            ? recipients.filter((r) => r.username.toLowerCase().includes(q))
            : recipients;

        if (!filtered.length) {
            listEl.innerHTML = '<div class="text-center py-4 text-muted small">Không tìm thấy người nhận</div>';
            return;
        }

        listEl.innerHTML = filtered.map((r) => `
            <label class="share-recipient-item">
                <input type="checkbox" class="form-check-input share-recipient-check" value="${r.id}"
                       data-conversation-id="${r.conversation_id || ''}">
                <img src="${r.avatar}" alt="" class="share-recipient-avatar" loading="lazy">
                <span class="share-recipient-name">${r.username}</span>
                ${r.source === 'recent' ? '<span class="share-recipient-badge">Gần đây</span>' : ''}
            </label>
        `).join('');
    }

    function loadRecipients(modal) {
        const listEl = modal.querySelector('.share-recipients-list');
        if (!listEl || listEl.dataset.loaded === 'true') return;

        const url = modal.dataset.recipientsUrl;
        fetch(url, {
            headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status !== 'success') {
                    throw new Error(data.message || 'Không tải được danh sách người nhận');
                }
                modal._shareRecipients = data.recipients || [];
                listEl.dataset.loaded = 'true';
                renderRecipients(modal, modal._shareRecipients, modal.querySelector('.share-recipient-search')?.value);
            })
            .catch((err) => {
                listEl.innerHTML = `<div class="text-center py-4 text-danger small">${err.message || 'Lỗi tải danh sách'}</div>`;
            });
    }

    function shareToFeed(modal) {
        if (isCommentMode(modal)) {
            alert('Bình luận chỉ có thể chia sẻ qua tin nhắn.');
            return;
        }

        const postId = modal.querySelector('.share-post-id')?.value;
        const caption = modal.querySelector('.share-caption')?.value || '';
        const submitBtn = modal.querySelector('.share-feed-submit');
        const url = modal.dataset.shareUrl || '/posts/share/';

        if (!postId) {
            alert('Không tìm thấy bài viết để chia sẻ.');
            return;
        }

        setButtonLoading(submitBtn, true);

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(modal),
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
            },
            body: JSON.stringify({
                post_id: postId,
                caption,
                as_new_post: true,
            }),
        })
            .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                if (!ok || data.status !== 'success') {
                    throw new Error(data.message || 'Có lỗi xảy ra khi chia sẻ bài viết.');
                }

                const instance = bootstrap.Modal.getInstance(modal);
                if (instance) instance.hide();

                if (data.post_id) {
                    window.location.href = `/posts/${data.post_id}/`;
                } else {
                    window.location.reload();
                }
            })
            .catch((err) => alert(err.message || 'Có lỗi xảy ra khi chia sẻ bài viết.'))
            .finally(() => setButtonLoading(submitBtn, false));
    }

    function shareViaMessage(modal) {
        const postId = modal.querySelector('.share-post-id')?.value;
        const commentId = modal.querySelector('.share-comment-id')?.value || '';
        const message = modal.querySelector('.share-dm-message')?.value || '';
        const submitBtn = modal.querySelector('.share-dm-submit');
        const url = modal.dataset.dmUrl || '/posts/share/via-message/';
        const selectedChecks = [...modal.querySelectorAll('.share-recipient-check:checked')];
        const selected = selectedChecks.map((el) => el.value);
        const conversationIds = {};
        selectedChecks.forEach((el) => {
            const cid = el.getAttribute('data-conversation-id');
            if (cid) conversationIds[el.value] = cid;
        });

        if (!postId) {
            alert(commentId ? 'Không tìm thấy bài viết của bình luận.' : 'Không tìm thấy bài viết để chia sẻ.');
            return;
        }
        if (!selected.length) {
            alert('Vui lòng chọn ít nhất một người nhận.');
            return;
        }

        setButtonLoading(submitBtn, true);

        const payload = {
            post_id: postId,
            recipient_ids: selected,
            conversation_ids: conversationIds,
            message,
        };
        if (commentId) payload.comment_id = commentId;

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(modal),
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
            },
            body: JSON.stringify(payload),
        })
            .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                if (!ok || data.status !== 'success') {
                    throw new Error(data.message || 'Không thể gửi tin nhắn.');
                }

                const instance = bootstrap.Modal.getInstance(modal);
                if (instance) instance.hide();

                modal.querySelectorAll('.share-recipient-check').forEach((el) => { el.checked = false; });
                const dmMessage = modal.querySelector('.share-dm-message');
                if (dmMessage) dmMessage.value = '';

                alert(data.message || 'Đã gửi tin nhắn thành công!');
            })
            .catch((err) => alert(err.message || 'Không thể gửi tin nhắn.'))
            .finally(() => setButtonLoading(submitBtn, false));
    }

    function initShareModal(modal) {
        if (modal.dataset.shareInitialized === 'true') return;
        modal.dataset.shareInitialized = 'true';

        const suffix = modal.dataset.modalSuffix || '';

        modal.querySelectorAll('.share-tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => switchShareTab(modal, btn.dataset.shareTab));
        });

        modal.querySelector('.share-feed-submit')?.addEventListener('click', () => shareToFeed(modal));
        modal.querySelector('.share-dm-submit')?.addEventListener('click', () => shareViaMessage(modal));

        modal.querySelector('.share-recipient-search')?.addEventListener('input', (e) => {
            if (!modal._shareRecipients) return;
            renderRecipients(modal, modal._shareRecipients, e.target.value);
        });

        modal.addEventListener('hidden.bs.modal', () => {
            resetCommentMode(modal);
            switchShareTab(modal, `feed${suffix}`);
            const listEl = modal.querySelector('.share-recipients-list');
            if (listEl) {
                listEl.dataset.loaded = 'false';
                listEl.innerHTML = `
                    <div class="text-center py-4 share-recipients-loading">
                        <div class="spinner-border spinner-border-sm text-secondary" role="status"></div>
                        <span class="ms-2 text-muted small">Đang tải...</span>
                    </div>`;
            }
            modal._shareRecipients = null;
        });
    }

    function prepareSharePost(modal, postId) {
        if (!modal) return;
        resetCommentMode(modal);
        const input = modal.querySelector('.share-post-id');
        if (input && postId) input.value = postId;
    }

    function openShareCommentModal(postId, commentId) {
        const modal = document.getElementById('sharePostModal');
        if (!modal) {
            alert('Không tìm thấy hộp thoại chia sẻ.');
            return;
        }
        if (!postId || !commentId) {
            alert('Thiếu thông tin bình luận để chia sẻ.');
            return;
        }

        initShareModal(modal);

        const postInput = modal.querySelector('.share-post-id');
        const commentInput = modal.querySelector('.share-comment-id');
        if (postInput) postInput.value = postId;
        if (commentInput) commentInput.value = commentId;

        setCommentMode(modal, true);
        const suffix = modal.dataset.modalSuffix || '';
        switchShareTab(modal, `message${suffix}`);

        const instance = bootstrap.Modal.getOrCreateInstance(modal);
        instance.show();
    }

    function bindShareButtons(scope) {
        (scope || document).querySelectorAll('.share-button:not([data-share-bound])').forEach((button) => {
            button.dataset.shareBound = 'true';
            button.addEventListener('click', () => {
                const postId = button.getAttribute('data-post-id');
                const targetSelector = button.getAttribute('data-bs-target');
                const modal = targetSelector
                    ? document.querySelector(targetSelector)
                    : document.getElementById('sharePostModal');
                prepareSharePost(modal, postId);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.share-post-modal').forEach(initShareModal);
        bindShareButtons();
    });

    window.initSharePostModals = function (scope) {
        (scope || document).querySelectorAll('.share-post-modal').forEach(initShareModal);
        bindShareButtons(scope);
    };

    window.openShareCommentModal = openShareCommentModal;
})();
