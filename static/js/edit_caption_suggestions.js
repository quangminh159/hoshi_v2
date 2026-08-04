(function (window) {
    'use strict';

    function getCurrentWord(text, caretPos) {
        const before = text.substring(0, caretPos);
        const parts = before.split(/\s+/);
        return parts[parts.length - 1] || '';
    }

    function replaceCurrentWord(textarea, replacement) {
        const text = textarea.value;
        const caretPos = textarea.selectionStart;
        const before = text.substring(0, caretPos);
        const after = text.substring(caretPos);
        const start = before.lastIndexOf(getCurrentWord(text, caretPos));
        const newText = before.substring(0, start) + replacement + after;
        textarea.value = newText;
        const newPos = start + replacement.length;
        textarea.setSelectionRange(newPos, newPos);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    /**
     * Gắn gợi ý #hashtag và @mention (chỉ người đang follow) cho textarea chỉnh sửa.
     * @param {HTMLTextAreaElement} textarea
     * @param {{hashtagUrl: string, userUrl: string, box?: HTMLElement}} options
     */
    window.initEditCaptionSuggestions = function (textarea, options) {
        if (!textarea || textarea.dataset.captionSuggestBound === '1') return;
        textarea.dataset.captionSuggestBound = '1';

        const hashtagUrl = options.hashtagUrl;
        const userUrl = options.userUrl;
        let box = options.box;
        if (!box) {
            box = document.createElement('div');
            box.className = 'edit-caption-suggestion-box';
            const wrap = textarea.closest('.position-relative') || textarea.parentElement;
            if (wrap && !wrap.classList.contains('position-relative')) {
                wrap.classList.add('position-relative');
            }
            (wrap || textarea.parentElement).appendChild(box);
        }

        let timeout = null;
        let mode = null;

        function clearBox() {
            box.innerHTML = '';
            mode = null;
        }

        function showItems(items, onSelect) {
            clearBox();
            if (!items.length) return;

            const dropdown = document.createElement('div');
            dropdown.className = 'suggestion-dropdown';

            items.forEach((item) => {
                const el = document.createElement('div');
                el.className = 'suggestion-item';
                el.innerHTML = item.html;
                el.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    onSelect(item);
                    clearBox();
                    textarea.focus();
                });
                dropdown.appendChild(el);
            });

            box.appendChild(dropdown);
        }

        textarea.addEventListener('input', function () {
            clearTimeout(timeout);
            const caretPos = this.selectionStart;
            const word = getCurrentWord(this.value, caretPos);

            if (word.startsWith('#') && word.length > 1) {
                mode = 'hashtag';
                const query = word.substring(1);
                timeout = setTimeout(() => {
                    fetch(`${hashtagUrl}?q=${encodeURIComponent(query)}`)
                        .then((r) => r.json())
                        .then((tags) => {
                            if (mode !== 'hashtag') return;
                            const list = Array.isArray(tags) ? tags : [];
                            const items = list.map((tag) => {
                                const name = typeof tag === 'string' ? tag : (tag.name || '');
                                const count = typeof tag === 'object' ? (tag.posts_count || 0) : 0;
                                const isNew = typeof tag === 'object' && tag.is_new;
                                const meta = isNew
                                    ? 'Hashtag mới'
                                    : (count > 0 ? `${count} bài viết` : 'Hashtag');
                                return {
                                    html: `<div>
                                             <div class="fw-semibold hashtag-link">#${name}</div>
                                             <div class="location-meta">${meta}</div>
                                           </div>`,
                                    value: '#' + name + ' ',
                                };
                            }).filter((item) => item.value.length > 2);

                            showItems(items, (item) => replaceCurrentWord(textarea, item.value));
                        })
                        .catch(clearBox);
                }, 250);
                return;
            }

            if (word.startsWith('@') && word.length > 1) {
                mode = 'user';
                const query = word.substring(1);
                timeout = setTimeout(() => {
                    fetch(`${userUrl}?q=${encodeURIComponent(query)}&following_only=true`)
                        .then((r) => r.json())
                        .then((users) => {
                            if (mode !== 'user') return;
                            const list = Array.isArray(users) ? users : [];
                            showItems(
                                list.map((user) => ({
                                    html: `<img src="${user.avatar_url || '/static/images/default-avatar.png'}" alt="">
                                           <div>
                                             <div class="fw-semibold">@${user.username}</div>
                                             ${user.full_name ? `<div class="location-meta">${user.full_name}</div>` : ''}
                                           </div>`,
                                    value: '@' + user.username + ' ',
                                })),
                                (item) => replaceCurrentWord(textarea, item.value)
                            );
                        })
                        .catch(clearBox);
                }, 250);
                return;
            }

            clearBox();
        });

        document.addEventListener('click', (e) => {
            if (e.target !== textarea && !box.contains(e.target)) {
                clearBox();
            }
        });
    };
})(window);
