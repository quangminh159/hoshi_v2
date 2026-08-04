(function () {
    const IMAGE_EXT = /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i;
    const VIDEO_EXT = /\.(mp4|mov|mkv|webm|avi|m4v|wmv|3gp|3gpp|mpeg|mpg|flv|ts|mts)$/i;

    function isImageFile(file) {
        const type = (file.type || '').toLowerCase();
        const name = (file.name || '').toLowerCase();
        return type.startsWith('image/') || IMAGE_EXT.test(name);
    }

    function isVideoFile(file) {
        const type = (file.type || '').toLowerCase();
        const name = (file.name || '').toLowerCase();
        return type.startsWith('video/') || VIDEO_EXT.test(name);
    }

    function isAllowedFile(file) {
        return isImageFile(file) || isVideoFile(file);
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    window.resetCreatePostComposer = function (scope) {
        const root = scope || document;
        const form = root.querySelector('#postForm');
        if (!form) return;

        const caption = root.querySelector('#caption');
        const location = root.querySelector('#location');
        const suggestionBox = root.querySelector('#suggestionBox');
        const locationSuggestionBox = root.querySelector('#locationSuggestionBox');

        if (caption) caption.value = '';
        if (location) location.value = '';
        if (suggestionBox) suggestionBox.innerHTML = '';
        if (locationSuggestionBox) locationSuggestionBox.innerHTML = '';

        if (form._createPostPond) {
            form._createPostPond.removeFiles();
        }
    };

    window.initCreatePostComposer = function (config) {
        const scope = config.scope || document;
        const form = scope.querySelector('#postForm');
        if (!form || form.dataset.composerInitialized === '1') {
            return form ? form._createPostPond : null;
        }

        form.dataset.composerInitialized = '1';

        if (typeof FilePond !== 'undefined') {
            FilePond.registerPlugin(
                FilePondPluginImageExifOrientation,
                FilePondPluginImagePreview,
                FilePondPluginFilePoster,
                FilePondPluginMediaPreview
            );
        }

        const fileInput = scope.querySelector('input.filepond');
        const pond = FilePond.create(fileInput, {
            allowMultiple: true,
            allowReorder: true,
            storeAsFile: true,
            allowVideoPreview: true,
            labelIdle: '<i class="fas fa-cloud-upload-alt mb-1 d-block" style="color:#c7c7c7;font-size:1.25rem"></i>Kéo thả hoặc <span class="filepond--label-action">chọn file</span>',
            labelFileTypeNotAllowed: 'Loại file không được hỗ trợ',
            stylePanelLayout: 'compact',
            styleItemPanelAspectRatio: 1,
            imagePreviewHeight: 96,
            beforeAddFile: (item) => {
                const file = item.file || item;
                if (!isAllowedFile(file)) {
                    alert('File không được hỗ trợ. Vui lòng chọn ảnh hoặc video.');
                    return false;
                }
                return true;
            },
        });
        form._createPostPond = pond;

        const captionInput = scope.querySelector('#caption');
        const suggestionBox = scope.querySelector('#suggestionBox');
        const locationInput = scope.querySelector('#location');
        const locationSuggestionBox = scope.querySelector('#locationSuggestionBox');
        const btnCurrentLocation = scope.querySelector('#btnCurrentLocation');
        let suggestionTimeout = null;
        let locationTimeout = null;

        function clearSuggestions() {
            if (suggestionBox) suggestionBox.innerHTML = '';
        }

        function clearLocationSuggestions() {
            if (locationSuggestionBox) locationSuggestionBox.innerHTML = '';
        }

        function getWordAtCaret(text, caretPos) {
            const before = text.substring(0, caretPos);
            const parts = before.split(/\s+/);
            return parts[parts.length - 1] || '';
        }

        function replaceWordAtCaret(textarea, replacement) {
            const text = textarea.value;
            const caretPos = textarea.selectionStart;
            const before = text.substring(0, caretPos);
            const after = text.substring(caretPos);
            const word = getWordAtCaret(text, caretPos);
            const start = before.lastIndexOf(word);
            const newText = before.substring(0, start) + replacement + after;
            textarea.value = newText;
            const newPos = start + replacement.length;
            textarea.setSelectionRange(newPos, newPos);
        }

        function showSuggestions(items, onSelect) {
            clearSuggestions();
            if (!items.length || !suggestionBox) return;

            const dropdown = document.createElement('div');
            dropdown.className = 'suggestion-dropdown suggestion-dropdown--caption';

            items.forEach(item => {
                const el = document.createElement('div');
                el.className = 'suggestion-item';
                el.innerHTML = item.html;
                el.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    onSelect(item);
                    clearSuggestions();
                    if (captionInput) captionInput.focus();
                });
                dropdown.appendChild(el);
            });

            suggestionBox.appendChild(dropdown);
            // Đảm bảo dropdown không bị cắt / ẩn
            suggestionBox.style.display = 'block';
        }

        function showLocationSuggestions(items) {
            clearLocationSuggestions();
            if (!items.length || !locationSuggestionBox) return;

            const dropdown = document.createElement('div');
            dropdown.className = 'suggestion-dropdown';

            items.forEach(item => {
                const el = document.createElement('div');
                el.className = 'suggestion-item location-suggestion-item';
                const sourceLabel = item.source === 'recent' ? 'Đã dùng gần đây' : 'Địa điểm';
                el.innerHTML = `
                    <div>
                        <div>${item.name}</div>
                        ${item.full_name && item.full_name !== item.name
                            ? `<div class="location-meta">${item.full_name}</div>`
                            : `<div class="location-meta">${sourceLabel}</div>`}
                    </div>
                `;
                el.addEventListener('click', () => {
                    locationInput.value = item.name;
                    clearLocationSuggestions();
                });
                dropdown.appendChild(el);
            });

            locationSuggestionBox.appendChild(dropdown);
        }

        if (captionInput) {
            captionInput.addEventListener('input', function () {
                clearTimeout(suggestionTimeout);
                const caretPos = this.selectionStart;
                const text = this.value;
                const lastWord = getWordAtCaret(text, caretPos);

                if (!lastWord.startsWith('#') && !lastWord.startsWith('@')) {
                    clearSuggestions();
                    return;
                }

                suggestionTimeout = setTimeout(() => {
                    const query = lastWord.substring(1);
                    if (!query) {
                        clearSuggestions();
                        return;
                    }

                    if (lastWord.startsWith('#')) {
                        fetch(`${config.hashtagUrl}?q=${encodeURIComponent(query)}`)
                            .then(r => r.json())
                            .then(tags => {
                                const list = Array.isArray(tags) ? tags : [];
                                const items = list.map((tag) => {
                                    // Hỗ trợ cả API cũ (string) và mới (object)
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

                                showSuggestions(items, (item) => {
                                    replaceWordAtCaret(captionInput, item.value);
                                });
                            })
                            .catch(() => clearSuggestions());
                    } else {
                        fetch(`${config.userUrl}?q=${encodeURIComponent(query)}&following_only=true`)
                            .then(r => r.json())
                            .then(users => {
                                showSuggestions((users || []).map(user => ({
                                    html: `<img src="${user.avatar_url || '/static/images/default-avatar.png'}" alt="">
                                           <div>
                                             <div class="fw-semibold">@${user.username}</div>
                                             ${user.full_name ? `<div class="location-meta">${user.full_name}</div>` : ''}
                                           </div>`,
                                    value: '@' + user.username + ' ',
                                })), (item) => {
                                    replaceWordAtCaret(captionInput, item.value);
                                });
                            })
                            .catch(() => clearSuggestions());
                    }
                }, 250);
            });
        }

        if (locationInput) {
            locationInput.addEventListener('input', function () {
                clearTimeout(locationTimeout);
                const query = this.value.trim();
                if (query.length < 2) {
                    clearLocationSuggestions();
                    return;
                }

                locationTimeout = setTimeout(() => {
                    fetch(`${config.locationUrl}?q=${encodeURIComponent(query)}`)
                        .then(r => r.json())
                        .then(items => showLocationSuggestions(items))
                        .catch(() => clearLocationSuggestions());
                }, 300);
            });

            locationInput.addEventListener('focus', function () {
                const query = this.value.trim();
                if (query.length >= 2) {
                    fetch(`${config.locationUrl}?q=${encodeURIComponent(query)}`)
                        .then(r => r.json())
                        .then(items => showLocationSuggestions(items));
                }
            });
        }

        if (btnCurrentLocation) {
            btnCurrentLocation.addEventListener('click', function () {
                if (!navigator.geolocation) {
                    alert('Trình duyệt không hỗ trợ định vị GPS.');
                    return;
                }

                const icon = this.querySelector('i');
                const originalClass = icon.className;
                icon.className = 'fas fa-spinner fa-spin';
                this.disabled = true;

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const { latitude, longitude } = position.coords;
                        fetch(`${config.reverseGeocodeUrl}?lat=${latitude}&lon=${longitude}`)
                            .then(r => r.json())
                            .then(data => {
                                if (data.error) throw new Error(data.error);
                                locationInput.value = data.name;
                                clearLocationSuggestions();
                            })
                            .catch(err => alert(err.message || 'Không thể lấy vị trí hiện tại.'))
                            .finally(() => {
                                icon.className = originalClass;
                                btnCurrentLocation.disabled = false;
                            });
                    },
                    () => {
                        alert('Không thể truy cập vị trí. Vui lòng cho phép quyền định vị.');
                        icon.className = originalClass;
                        btnCurrentLocation.disabled = false;
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            });
        }

        document.addEventListener('click', (e) => {
            if (suggestionBox && !suggestionBox.contains(e.target) && e.target !== captionInput) {
                clearSuggestions();
            }
            if (locationSuggestionBox && !locationSuggestionBox.contains(e.target)
                && e.target !== locationInput && e.target !== btnCurrentLocation) {
                clearLocationSuggestions();
            }
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            const submitButton = this.querySelector('button[type="submit"]');
            const defaultButtonHtml = '<i class="fas fa-paper-plane"></i><span>Đăng bài</span>';

            function resetSubmitButton() {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = defaultButtonHtml;
                }
                form.classList.remove('submitting');
            }

            if (pond.getFiles().length === 0 && !(captionInput.value || '').trim()) {
                alert('Vui lòng nhập nội dung hoặc chọn ít nhất một ảnh/video');
                resetSubmitButton();
                return;
            }

            const MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024;
            const oversizedFiles = pond.getFiles()
                .map(f => f.file)
                .filter(f => f && f.size > MAX_FILE_SIZE)
                .map(f => f.name);

            if (oversizedFiles.length > 0) {
                alert(`File vượt quá 1GB: ${oversizedFiles.join(', ')}`);
                resetSubmitButton();
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Đang đăng...</span>';
            }

            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCsrfToken());
            formData.append('caption', captionInput.value);
            formData.append('location', locationInput ? locationInput.value : '');

            pond.getFiles().forEach((fileItem) => {
                const file = fileItem.file || fileItem.source;
                if (file instanceof File || file instanceof Blob) {
                    formData.append('media', file, file.name || fileItem.filename || 'upload');
                }
            });

            fetch(config.createUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
                credentials: 'same-origin',
            })
                .then(async (response) => {
                    const contentType = response.headers.get('content-type') || '';
                    if (contentType.includes('application/json')) {
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Không thể đăng bài.');
                        if (typeof config.onSuccess === 'function') {
                            config.onSuccess(data);
                        } else {
                            window.location.href = data.redirect_url || config.indexUrl;
                        }
                        return;
                    }
                    if (response.ok || response.redirected) {
                        window.location.href = response.url || config.indexUrl;
                        return;
                    }
                    throw new Error('Không thể đăng bài. Vui lòng thử lại.');
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert(error.message || 'Có lỗi xảy ra khi đăng bài.');
                    resetSubmitButton();
                });
        }, true);

        return pond;
    };
})();
