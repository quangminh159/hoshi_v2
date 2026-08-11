(function (window) {
    'use strict';

    function getCurrentWord(text, caretPos) {
        const before = text.substring(0, caretPos);
        const parts = before.split(/\s+/);
        return parts[parts.length - 1] || '';
    }

    function replaceCurrentWord(field, replacement) {
        const text = field.value;
        const caretPos = field.selectionStart;
        const before = text.substring(0, caretPos);
        const after = text.substring(caretPos);
        const word = getCurrentWord(text, caretPos);
        const start = before.lastIndexOf(word);
        const newText = before.substring(0, start) + replacement + after;
        field.value = newText;
        const newPos = start + replacement.length;
        field.setSelectionRange(newPos, newPos);
        field.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function buildMentionHighlightHtml(text) {
        const escaped = escapeHtml(text || '');
        // Giữ khoảng trắng / xuống dòng khớp input
        return escaped
            .replace(/@([A-Za-z0-9_.]+)/g, '<mark class="mention-chip">@$1</mark>')
            .replace(/#([A-Za-z0-9_]+)/g, '<mark class="hashtag-chip">#$1</mark>')
            .replace(/\n$/g, '\n ');
    }

    /**
     * Làm nổi @mention / #hashtag ngay trong ô nhập (overlay).
     * Quan trọng: không đổi font-weight/padding trong backdrop kẻo lệch caret.
     */
    window.initMentionInputHighlight = function (field) {
        if (!field || field.dataset.mentionHighlightBound === '1') return;
        field.dataset.mentionHighlightBound = '1';

        let wrap = field.closest('.mention-input-wrap');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'mention-input-wrap';
            field.parentNode.insertBefore(wrap, field);
            wrap.appendChild(field);
        }

        let backdrop = wrap.querySelector('.mention-input-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'mention-input-backdrop';
            backdrop.setAttribute('aria-hidden', 'true');
            wrap.insertBefore(backdrop, field);
        }

        field.classList.add('mention-input-field');

        function syncStyles() {
            const cs = window.getComputedStyle(field);
            const props = [
                'fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
                'fontVariant', 'letterSpacing', 'textTransform', 'lineHeight',
                'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
                'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
                'boxSizing', 'textAlign', 'direction',
            ];
            props.forEach((prop) => {
                backdrop.style[prop] = cs[prop];
            });
            backdrop.style.borderStyle = 'solid';
            backdrop.style.borderColor = 'transparent';
            backdrop.style.whiteSpace = field.tagName === 'TEXTAREA' ? 'pre-wrap' : 'pre';
            backdrop.style.wordWrap = 'break-word';
            backdrop.style.overflowWrap = 'break-word';
        }

        function sync() {
            syncStyles();
            backdrop.innerHTML = buildMentionHighlightHtml(field.value);
            backdrop.scrollTop = field.scrollTop;
            backdrop.scrollLeft = field.scrollLeft;
        }

        field._syncMentionHighlight = sync;
        field.addEventListener('input', sync);
        field.addEventListener('scroll', sync);
        field.addEventListener('change', sync);
        // Khi code gán field.value = '' (không fire input), vẫn xóa overlay
        const valueDesc = Object.getOwnPropertyDescriptor(
            field.tagName === 'TEXTAREA'
                ? HTMLTextAreaElement.prototype
                : HTMLInputElement.prototype,
            'value'
        );
        if (valueDesc && valueDesc.set && !field.dataset.mentionValuePatched) {
            field.dataset.mentionValuePatched = '1';
            Object.defineProperty(field, 'value', {
                get() {
                    return valueDesc.get.call(this);
                },
                set(v) {
                    valueDesc.set.call(this, v);
                    // sync ngay sau khi gán value từ JS
                    if (typeof this._syncMentionHighlight === 'function') {
                        this._syncMentionHighlight();
                    }
                },
                configurable: true,
            });
        }
        window.addEventListener('resize', syncStyles);
        requestAnimationFrame(sync);
    };

    window.syncMentionInputHighlight = function (field) {
        if (field && typeof field._syncMentionHighlight === 'function') {
            field._syncMentionHighlight();
        }
    };

    /**
     * Gắn gợi ý #hashtag và/hoặc @mention cho textarea/input.
     * @param {HTMLTextAreaElement|HTMLInputElement} field
     * @param {{
     *   hashtagUrl?: string,
     *   userUrl: string,
     *   box?: HTMLElement,
     *   mentionsOnly?: boolean,
     *   followingOnly?: boolean,
     *   placement?: 'below'|'above',
     * }} options
     */
    window.initEditCaptionSuggestions = function (field, options) {
        if (!field || field.dataset.captionSuggestBound === '1') return;
        field.dataset.captionSuggestBound = '1';

        if (typeof window.initMentionInputHighlight === 'function') {
            window.initMentionInputHighlight(field);
        }

        const hashtagUrl = options.hashtagUrl || '';
        const userUrl = options.userUrl;
        const mentionsOnly = !!options.mentionsOnly;
        const followingOnly = options.followingOnly !== false;
        const placement = options.placement || 'below';

        let box = options.box;
        if (!box) {
            box = document.createElement('div');
            box.className = mentionsOnly
                ? 'edit-caption-suggestion-box comment-mention-suggestion-box'
                : 'edit-caption-suggestion-box';
            if (placement === 'above') {
                box.classList.add('suggestion-box--above');
            }
            const wrap = field.closest('.position-relative')
                || field.closest('.input-group')?.parentElement
                || field.parentElement;
            if (wrap && !wrap.classList.contains('position-relative')) {
                wrap.classList.add('position-relative');
            }
            (wrap || field.parentElement).appendChild(box);
        } else if (placement === 'above') {
            box.classList.add('suggestion-box--above');
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
            if (placement === 'above') {
                dropdown.classList.add('suggestion-dropdown--above');
            }

            items.forEach((item) => {
                const el = document.createElement('div');
                el.className = 'suggestion-item';
                el.innerHTML = item.html;
                el.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    onSelect(item);
                    clearBox();
                    field.focus();
                });
                dropdown.appendChild(el);
            });

            box.appendChild(dropdown);
        }

        field.addEventListener('input', function () {
            clearTimeout(timeout);
            const caretPos = this.selectionStart;
            const word = getCurrentWord(this.value, caretPos);

            if (!mentionsOnly && hashtagUrl && word.startsWith('#') && word.length > 1) {
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

                            showItems(items, (item) => replaceCurrentWord(field, item.value));
                        })
                        .catch(clearBox);
                }, 250);
                return;
            }

            if (userUrl && word.startsWith('@') && word.length > 1) {
                mode = 'user';
                const query = word.substring(1);
                const followParam = followingOnly ? 'true' : 'false';
                timeout = setTimeout(() => {
                    fetch(`${userUrl}?q=${encodeURIComponent(query)}&following_only=${followParam}`)
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
                                (item) => replaceCurrentWord(field, item.value)
                            );
                        })
                        .catch(clearBox);
                }, 250);
                return;
            }

            clearBox();
        });

        document.addEventListener('click', (e) => {
            if (e.target !== field && !box.contains(e.target)) {
                clearBox();
            }
        });
    };

    /**
     * Gợi ý @mention cho ô bình luận (feed / chi tiết bài / sửa cmt).
     */
    window.initCommentMentionSuggestions = function (field, options) {
        if (!field) return;
        const opts = options || {};
        const userUrl = opts.userUrl || window.HOSHI_USER_SUGGESTIONS_URL;
        if (!userUrl) return;
        window.initEditCaptionSuggestions(field, {
            userUrl: userUrl,
            mentionsOnly: true,
            followingOnly: opts.followingOnly !== false,
            placement: opts.placement || 'above',
            box: opts.box,
        });
    };
})(window);
