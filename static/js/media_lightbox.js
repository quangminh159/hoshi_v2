/**
 * Hoshi media lightbox — xem ảnh/video phóng to, cấu hình video, lưu về máy.
 */
(function () {
    'use strict';

    const PREFS_KEY = 'hoshiVideoPrefs';
    const DEFAULT_PREFS = {
        speed: 1,
        loop: true,
        muted: false,
        volume: 1,
        fit: 'contain',
        resolution: 'auto', // auto | source | 1080 | 720 | 480 | 360
    };
    const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const RES_LADDER = [1080, 720, 480, 360];

    const state = {
        open: false,
        items: [],
        index: 0,
        scale: 1,
        tx: 0,
        ty: 0,
        dragging: false,
        startX: 0,
        startY: 0,
        originTx: 0,
        originTy: 0,
        prefs: loadPrefs(),
        settingsOpen: false,
    };

    let root;
    let stage;
    let mediaWrap;
    let counterEl;
    let prevBtn;
    let nextBtn;
    let zoomInBtn;
    let zoomOutBtn;
    let saveBtn;
    let closeBtn;
    let settingsBtn;
    let settingsPanel;
    let hintEl;

    function loadPrefs() {
        try {
            const raw = localStorage.getItem(PREFS_KEY);
            if (!raw) return { ...DEFAULT_PREFS };
            return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
        } catch (_) {
            return { ...DEFAULT_PREFS };
        }
    }

    function savePrefs() {
        try {
            localStorage.setItem(PREFS_KEY, JSON.stringify(state.prefs));
        } catch (_) {}
    }

    function ensureDom() {
        if (root) return;
        root = document.createElement('div');
        root.className = 'hoshi-lightbox';
        root.setAttribute('role', 'dialog');
        root.setAttribute('aria-modal', 'true');
        root.setAttribute('aria-label', 'Xem media');
        root.innerHTML = `
            <div class="hoshi-lightbox__toolbar">
                <span class="hoshi-lightbox__counter" data-lb-counter>1 / 1</span>
                <div class="hoshi-lightbox__actions">
                    <button type="button" class="hoshi-lightbox__btn" data-lb-zoom-out title="Thu nhỏ" aria-label="Thu nhỏ">
                        <i class="fas fa-search-minus"></i>
                    </button>
                    <button type="button" class="hoshi-lightbox__btn" data-lb-zoom-in title="Phóng to" aria-label="Phóng to">
                        <i class="fas fa-search-plus"></i>
                    </button>
                    <button type="button" class="hoshi-lightbox__btn" data-lb-settings title="Cấu hình video" aria-label="Cấu hình video" hidden>
                        <i class="fas fa-cog"></i>
                    </button>
                    <button type="button" class="hoshi-lightbox__btn" data-lb-save title="Lưu về máy" aria-label="Lưu về máy">
                        <i class="fas fa-download"></i>
                    </button>
                    <button type="button" class="hoshi-lightbox__btn" data-lb-close title="Đóng" aria-label="Đóng">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="hoshi-lightbox__settings" data-lb-settings-panel hidden>
                <div class="hoshi-lightbox__settings-title">Cấu hình video</div>
                <label class="hoshi-lightbox__settings-row">
                    <span>Tốc độ phát</span>
                    <select data-lb-speed>
                        ${SPEEDS.map((s) => `<option value="${s}">${s === 1 ? 'Bình thường (1x)' : s + 'x'}</option>`).join('')}
                    </select>
                </label>
                <label class="hoshi-lightbox__settings-row">
                    <span>Âm lượng</span>
                    <input type="range" min="0" max="1" step="0.05" data-lb-volume>
                </label>
                <label class="hoshi-lightbox__settings-row hoshi-lightbox__settings-row--toggle">
                    <span>Tắt tiếng</span>
                    <input type="checkbox" data-lb-muted>
                </label>
                <label class="hoshi-lightbox__settings-row hoshi-lightbox__settings-row--toggle">
                    <span>Phát lặp lại</span>
                    <input type="checkbox" data-lb-loop>
                </label>
                <label class="hoshi-lightbox__settings-row">
                    <span>Độ phân giải</span>
                    <select data-lb-resolution>
                        <option value="auto">Tự động</option>
                    </select>
                </label>
                <div class="hoshi-lightbox__settings-meta" data-lb-res-meta></div>
                <label class="hoshi-lightbox__settings-row">
                    <span>Hiển thị</span>
                    <select data-lb-fit>
                        <option value="contain">Vừa khung (không cắt)</option>
                        <option value="cover">Phủ khung (có thể cắt)</option>
                    </select>
                </label>
                <button type="button" class="hoshi-lightbox__settings-pip" data-lb-pip>
                    <i class="fas fa-external-link-alt"></i> Picture-in-Picture
                </button>
            </div>
            <button type="button" class="hoshi-lightbox__nav hoshi-lightbox__nav--prev" data-lb-prev aria-label="Trước">
                <i class="fas fa-chevron-left"></i>
            </button>
            <button type="button" class="hoshi-lightbox__nav hoshi-lightbox__nav--next" data-lb-next aria-label="Sau">
                <i class="fas fa-chevron-right"></i>
            </button>
            <div class="hoshi-lightbox__stage">
                <div class="hoshi-lightbox__media-wrap" data-lb-wrap></div>
            </div>
            <div class="hoshi-lightbox__hint" data-lb-hint>Cuộn để zoom · Esc để đóng</div>
        `;
        document.body.appendChild(root);

        stage = root.querySelector('.hoshi-lightbox__stage');
        mediaWrap = root.querySelector('[data-lb-wrap]');
        counterEl = root.querySelector('[data-lb-counter]');
        prevBtn = root.querySelector('[data-lb-prev]');
        nextBtn = root.querySelector('[data-lb-next]');
        zoomOutBtn = root.querySelector('[data-lb-zoom-out]');
        zoomInBtn = root.querySelector('[data-lb-zoom-in]');
        saveBtn = root.querySelector('[data-lb-save]');
        closeBtn = root.querySelector('[data-lb-close]');
        settingsBtn = root.querySelector('[data-lb-settings]');
        settingsPanel = root.querySelector('[data-lb-settings-panel]');
        hintEl = root.querySelector('[data-lb-hint]');

        closeBtn.addEventListener('click', close);
        prevBtn.addEventListener('click', () => showIndex(state.index - 1));
        nextBtn.addEventListener('click', () => showIndex(state.index + 1));
        zoomInBtn.addEventListener('click', () => setZoom(state.scale + 0.35));
        zoomOutBtn.addEventListener('click', () => setZoom(state.scale - 0.35));
        saveBtn.addEventListener('click', saveCurrent);
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSettings();
        });

        bindSettingsControls();

        root.addEventListener('click', (e) => {
            if (e.target === root || e.target === stage) {
                if (state.settingsOpen) {
                    closeSettings();
                    return;
                }
                close();
            }
        });

        mediaWrap.addEventListener('wheel', (e) => {
            if (!state.open) return;
            const item = state.items[state.index];
            if (!item || item.type !== 'image') return;
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.2 : 0.2;
            setZoom(state.scale + delta);
        }, { passive: false });

        mediaWrap.addEventListener('pointerdown', onPointerDown);
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('pointercancel', onPointerUp);

        document.addEventListener('keydown', (e) => {
            if (!state.open) return;
            if (e.key === 'Escape') {
                if (state.settingsOpen) closeSettings();
                else close();
            }
            if (e.key === 'ArrowLeft') showIndex(state.index - 1);
            if (e.key === 'ArrowRight') showIndex(state.index + 1);
            if (e.key === '+' || e.key === '=') setZoom(state.scale + 0.35);
            if (e.key === '-') setZoom(state.scale - 0.35);
            if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                saveCurrent();
            }
        });
    }

    function bindSettingsControls() {
        const speed = settingsPanel.querySelector('[data-lb-speed]');
        const volume = settingsPanel.querySelector('[data-lb-volume]');
        const muted = settingsPanel.querySelector('[data-lb-muted]');
        const loop = settingsPanel.querySelector('[data-lb-loop]');
        const fit = settingsPanel.querySelector('[data-lb-fit]');
        const resolution = settingsPanel.querySelector('[data-lb-resolution]');
        const pip = settingsPanel.querySelector('[data-lb-pip]');

        speed.value = String(state.prefs.speed);
        volume.value = String(state.prefs.volume);
        muted.checked = !!state.prefs.muted;
        loop.checked = !!state.prefs.loop;
        fit.value = state.prefs.fit === 'cover' ? 'cover' : 'contain';
        resolution.value = String(state.prefs.resolution || 'auto');

        speed.addEventListener('change', () => {
            state.prefs.speed = parseFloat(speed.value) || 1;
            savePrefs();
            applyVideoPrefs();
        });
        volume.addEventListener('input', () => {
            state.prefs.volume = parseFloat(volume.value);
            if (state.prefs.volume > 0) state.prefs.muted = false;
            muted.checked = state.prefs.muted;
            savePrefs();
            applyVideoPrefs();
        });
        muted.addEventListener('change', () => {
            state.prefs.muted = muted.checked;
            savePrefs();
            applyVideoPrefs();
        });
        loop.addEventListener('change', () => {
            state.prefs.loop = loop.checked;
            savePrefs();
            applyVideoPrefs();
            applyFeedVideoPrefs();
        });
        fit.addEventListener('change', () => {
            state.prefs.fit = fit.value;
            savePrefs();
            applyVideoPrefs();
        });
        resolution.addEventListener('change', () => {
            state.prefs.resolution = resolution.value;
            savePrefs();
            applyVideoPrefs();
        });
        pip.addEventListener('click', async () => {
            const video = currentVideo();
            if (!video || !document.pictureInPictureEnabled) return;
            try {
                if (document.pictureInPictureElement === video) {
                    await document.exitPictureInPicture();
                } else {
                    await video.requestPictureInPicture();
                }
            } catch (_) {}
        });

        if (!document.pictureInPictureEnabled) {
            pip.hidden = true;
        }
    }

    function labelForHeight(h) {
        if (h >= 2160) return '4K';
        if (h >= 1440) return '1440p';
        if (h >= 1080) return '1080p';
        if (h >= 720) return '720p';
        if (h >= 480) return '480p';
        if (h >= 360) return '360p';
        return `${h}p`;
    }

    function populateResolutionOptions(video) {
        const select = settingsPanel && settingsPanel.querySelector('[data-lb-resolution]');
        const meta = settingsPanel && settingsPanel.querySelector('[data-lb-res-meta]');
        if (!select) return;

        const srcW = video.videoWidth || 0;
        const srcH = video.videoHeight || 0;
        const preferred = String(state.prefs.resolution || 'auto');

        const options = [
            { value: 'auto', label: 'Tự động' },
        ];

        if (srcH > 0) {
            options.push({
                value: 'source',
                label: `Gốc (${srcW}×${srcH} · ${labelForHeight(srcH)})`,
            });
            RES_LADDER.forEach((h) => {
                if (h < srcH) {
                    const w = Math.round(h * (srcW / srcH));
                    options.push({
                        value: String(h),
                        label: `${labelForHeight(h)} (${w}×${h})`,
                    });
                }
            });
        }

        select.innerHTML = options.map((o) => (
            `<option value="${o.value}">${o.label}</option>`
        )).join('');

        const values = options.map((o) => o.value);
        select.value = values.includes(preferred) ? preferred : 'auto';
        if (!values.includes(preferred)) {
            state.prefs.resolution = 'auto';
            savePrefs();
        }

        if (meta) {
            meta.textContent = srcH
                ? `Nguồn: ${srcW}×${srcH} (${labelForHeight(srcH)})`
                : 'Đang đọc độ phân giải nguồn…';
        }
    }

    function syncSettingsForm() {
        if (!settingsPanel) return;
        settingsPanel.querySelector('[data-lb-speed]').value = String(state.prefs.speed);
        settingsPanel.querySelector('[data-lb-volume]').value = String(state.prefs.volume);
        settingsPanel.querySelector('[data-lb-muted]').checked = !!state.prefs.muted;
        settingsPanel.querySelector('[data-lb-loop]').checked = !!state.prefs.loop;
        settingsPanel.querySelector('[data-lb-fit]').value = state.prefs.fit === 'cover' ? 'cover' : 'contain';
        const video = currentVideo();
        if (video && video.videoHeight) populateResolutionOptions(video);
        else {
            const select = settingsPanel.querySelector('[data-lb-resolution]');
            if (select) select.value = String(state.prefs.resolution || 'auto');
        }
    }

    function toggleSettings() {
        if (state.settingsOpen) closeSettings();
        else openSettings();
    }

    function openSettings() {
        state.settingsOpen = true;
        syncSettingsForm();
        settingsPanel.hidden = false;
        settingsBtn.classList.add('is-active');
    }

    function closeSettings() {
        state.settingsOpen = false;
        settingsPanel.hidden = true;
        settingsBtn.classList.remove('is-active');
    }

    function currentVideo() {
        return mediaWrap ? mediaWrap.querySelector('video') : null;
    }

    function applyVideoPrefs() {
        const video = currentVideo();
        if (!video) return;

        video.playbackRate = state.prefs.speed || 1;
        video.loop = !!state.prefs.loop;
        video.muted = !!state.prefs.muted;
        video.volume = Math.min(1, Math.max(0, state.prefs.volume || 0));

        // Khung luôn full stage — không bao giờ co khung theo độ phân giải
        video.style.position = 'absolute';
        video.style.inset = '0';
        video.style.width = '100%';
        video.style.height = '100%';
        video.style.maxWidth = 'none';
        video.style.maxHeight = 'none';
        video.style.transform = 'none';
        video.style.objectFit = state.prefs.fit === 'cover' ? 'cover' : 'contain';
        video.style.objectPosition = 'center center';

        applyResolutionRender(video);
        updateResolutionMeta(video);
    }

    function applyResolutionRender(video) {
        stopResolutionCanvas();
        const srcH = video.videoHeight || 0;
        const srcW = video.videoWidth || 0;
        const res = String(state.prefs.resolution || 'auto');

        let targetH = null;
        if (res !== 'auto' && res !== 'source') {
            targetH = parseInt(res, 10) || null;
            if (!targetH || !srcH || targetH >= srcH) targetH = null;
        }

        video.style.opacity = '1';
        video.classList.remove('hoshi-lightbox__video--canvas-mode');
        if (!targetH || !srcW || !srcH) return;

        const canvas = document.createElement('canvas');
        canvas.className = 'hoshi-lightbox__res-canvas';
        mediaWrap.appendChild(canvas);
        video.classList.add('hoshi-lightbox__video--canvas-mode');

        const ctx = canvas.getContext('2d');
        const targetW = Math.max(2, Math.round(targetH * (srcW / srcH)));
        const controlsReserve = 56;

        const draw = () => {
            if (!state.open || currentVideo() !== video) {
                stopResolutionCanvas();
                return;
            }
            const wrapW = mediaWrap.clientWidth || 1;
            const wrapH = mediaWrap.clientHeight || 1;
            const drawH = Math.max(1, wrapH - controlsReserve);
            if (canvas.width !== wrapW || canvas.height !== drawH) {
                canvas.width = wrapW;
                canvas.height = drawH;
            }

            if (!state._resBuffer || state._resBuffer.width !== targetW || state._resBuffer.height !== targetH) {
                state._resBuffer = document.createElement('canvas');
                state._resBuffer.width = targetW;
                state._resBuffer.height = targetH;
            }
            const buf = state._resBuffer;
            const bctx = buf.getContext('2d');
            bctx.drawImage(video, 0, 0, targetW, targetH);

            ctx.clearRect(0, 0, wrapW, drawH);
            const fit = state.prefs.fit === 'cover' ? 'cover' : 'contain';
            let dw;
            let dh;
            if (fit === 'cover') {
                const scale = Math.max(wrapW / targetW, drawH / targetH);
                dw = targetW * scale;
                dh = targetH * scale;
            } else {
                const scale = Math.min(wrapW / targetW, drawH / targetH);
                dw = targetW * scale;
                dh = targetH * scale;
            }
            const dx = (wrapW - dw) / 2;
            const dy = (drawH - dh) / 2;
            ctx.imageSmoothingEnabled = true;
            ctx.drawImage(buf, dx, dy, dw, dh);
            state._resRaf = requestAnimationFrame(draw);
        };

        state._resRaf = requestAnimationFrame(draw);
    }

    function stopResolutionCanvas() {
        if (state._resRaf) {
            cancelAnimationFrame(state._resRaf);
            state._resRaf = null;
        }
        state._resBuffer = null;
        if (mediaWrap) {
            mediaWrap.querySelectorAll('.hoshi-lightbox__res-canvas').forEach((c) => c.remove());
            const video = mediaWrap.querySelector('video');
            if (video) {
                video.classList.remove('hoshi-lightbox__video--canvas-mode');
                video.style.opacity = '1';
            }
        }
    }

    function updateResolutionMeta(video) {
        const meta = settingsPanel && settingsPanel.querySelector('[data-lb-res-meta]');
        if (!meta) return;
        const srcW = video.videoWidth || 0;
        const srcH = video.videoHeight || 0;
        if (!srcH) {
            meta.textContent = 'Đang đọc độ phân giải nguồn…';
            return;
        }
        const res = String(state.prefs.resolution || 'auto');
        let current = 'Gốc';
        if (res === 'auto') current = 'Tự động';
        else if (res !== 'source') {
            const h = parseInt(res, 10);
            if (h && h < srcH) current = labelForHeight(h);
        }
        meta.textContent = `Nguồn ${srcW}×${srcH} (${labelForHeight(srcH)}) · Đang xem: ${current}`;
    }

    function applyFeedVideoPrefs() {
        document.querySelectorAll('video.feed-video, .carousel-item video').forEach((video) => {
            video.loop = !!state.prefs.loop;
            // Feed autoplay cần muted theo policy trình duyệt
            video.dataset.hoshiLoop = state.prefs.loop ? '1' : '0';
        });
    }

    function cleanUrl(url) {
        if (!url) return '';
        try {
            return new URL(url, window.location.origin).href;
        } catch (_) {
            return url;
        }
    }

    function filenameFromUrl(url, type) {
        try {
            const path = new URL(url, window.location.origin).pathname;
            const base = path.split('/').pop() || (type === 'video' ? 'video.mp4' : 'image.jpg');
            return base.split('?')[0] || base;
        } catch (_) {
            return type === 'video' ? 'hoshi-video.mp4' : 'hoshi-image.jpg';
        }
    }

    function collectFromCarousel(carousel, activeEl) {
        const items = [];
        carousel.querySelectorAll('.carousel-item').forEach((slide) => {
            const img = slide.querySelector('img');
            const video = slide.querySelector('video');
            if (img) {
                items.push({ type: 'image', src: cleanUrl(img.currentSrc || img.src) });
            } else if (video) {
                const src = video.currentSrc || video.getAttribute('src') || (video.querySelector('source') && video.querySelector('source').src);
                if (src) items.push({ type: 'video', src: cleanUrl(src) });
            }
        });
        let index = 0;
        if (activeEl) {
            const slide = activeEl.closest('.carousel-item');
            if (slide) {
                const all = Array.from(carousel.querySelectorAll('.carousel-item'));
                index = Math.max(0, all.indexOf(slide));
            }
        }
        return { items, index };
    }

    function resetTransform() {
        state.scale = 1;
        state.tx = 0;
        state.ty = 0;
        applyTransform();
    }

    function applyTransform() {
        const media = mediaWrap.querySelector('img, video');
        if (!media || media.tagName === 'VIDEO') return;
        media.style.transform = `translate(${state.tx}px, ${state.ty}px) scale(${state.scale})`;
    }

    function setZoom(next) {
        const current = state.items[state.index];
        if (!current || current.type === 'video') return;
        state.scale = Math.min(4, Math.max(1, next));
        if (state.scale === 1) {
            state.tx = 0;
            state.ty = 0;
        }
        applyTransform();
        zoomOutBtn.disabled = state.scale <= 1;
        zoomInBtn.disabled = state.scale >= 4;
    }

    function onPointerDown(e) {
        if (!state.open || state.scale <= 1) return;
        if (e.target.closest('video') || e.target.closest('.hoshi-lightbox__settings')) return;
        state.dragging = true;
        state.startX = e.clientX;
        state.startY = e.clientY;
        state.originTx = state.tx;
        state.originTy = state.ty;
        mediaWrap.classList.add('is-dragging');
        mediaWrap.setPointerCapture?.(e.pointerId);
    }

    function onPointerMove(e) {
        if (!state.dragging) return;
        state.tx = state.originTx + (e.clientX - state.startX);
        state.ty = state.originTy + (e.clientY - state.startY);
        applyTransform();
    }

    function onPointerUp() {
        state.dragging = false;
        mediaWrap.classList.remove('is-dragging');
    }

    function showIndex(i) {
        if (!state.items.length) return;
        const len = state.items.length;
        state.index = ((i % len) + len) % len;
        closeSettings();
        renderMedia();
    }

    function renderMedia() {
        const item = state.items[state.index];
        if (!item) return;
        resetTransform();
        mediaWrap.innerHTML = '';

        if (item.type === 'video') {
            const video = document.createElement('video');
            video.src = item.src;
            video.controls = true;
            video.autoplay = true;
            video.playsInline = true;
            video.setAttribute('controlsList', 'nodownload');
            mediaWrap.appendChild(video);
            const onMeta = () => {
                populateResolutionOptions(video);
                applyVideoPrefs();
            };
            if (video.readyState >= 1) onMeta();
            else video.addEventListener('loadedmetadata', onMeta, { once: true });
            applyVideoPrefs();
            zoomInBtn.disabled = true;
            zoomOutBtn.disabled = true;
            settingsBtn.hidden = false;
            hintEl.textContent = 'Bánh răng = cấu hình video · Esc để đóng';
        } else {
            const img = document.createElement('img');
            img.src = item.src;
            img.alt = 'Media';
            mediaWrap.appendChild(img);
            zoomInBtn.disabled = false;
            zoomOutBtn.disabled = true;
            settingsBtn.hidden = true;
            closeSettings();
            hintEl.textContent = 'Cuộn để zoom · Esc để đóng · kéo khi đã phóng to';
        }

        counterEl.textContent = `${state.index + 1} / ${state.items.length}`;
        const multi = state.items.length > 1;
        prevBtn.style.display = multi ? '' : 'none';
        nextBtn.style.display = multi ? '' : 'none';
    }

    function open(items, index) {
        if (!items || !items.length) return;
        ensureDom();
        state.prefs = loadPrefs();
        state.items = items;
        state.index = Math.max(0, Math.min(index || 0, items.length - 1));
        state.open = true;
        root.classList.add('is-open');
        document.body.classList.add('hoshi-lightbox-open');
        renderMedia();
        document.querySelectorAll('video.feed-video, .carousel-item video').forEach((v) => {
            try { v.pause(); } catch (_) {}
        });
    }

    function close() {
        if (!state.open) return;
        state.open = false;
        closeSettings();
        stopResolutionCanvas();
        const playing = mediaWrap.querySelector('video');
        if (playing) {
            try { playing.pause(); } catch (_) {}
        }
        mediaWrap.innerHTML = '';
        root.classList.remove('is-open');
        document.body.classList.remove('hoshi-lightbox-open');
    }

    async function saveCurrent() {
        const item = state.items[state.index];
        if (!item) return;
        const name = filenameFromUrl(item.src, item.type);
        saveBtn.disabled = true;
        try {
            const res = await fetch(item.src, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('fetch failed');
            const blob = await res.blob();
            const objectUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = objectUrl;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(objectUrl);
        } catch (_) {
            const a = document.createElement('a');
            a.href = item.src;
            a.target = '_blank';
            a.rel = 'noopener';
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } finally {
            saveBtn.disabled = false;
        }
    }

    function isInteractiveChrome(target) {
        return !!(
            target.closest('.carousel-control-prev') ||
            target.closest('.carousel-control-next') ||
            target.closest('.carousel-indicators') ||
            target.closest('button') ||
            target.closest('a') ||
            target.closest('.hoshi-lightbox') ||
            target.closest('.hoshi-video-settings-btn')
        );
    }

    function getCarouselInstance(carouselEl) {
        if (!carouselEl || !window.bootstrap || !bootstrap.Carousel) return null;
        return bootstrap.Carousel.getOrCreateInstance(carouselEl, {
            interval: false,
            ride: false,
            wrap: true,
            touch: true,
        });
    }

    function handleCarouselNavClick(e) {
        const prev = e.target.closest('.carousel-control-prev');
        const next = e.target.closest('.carousel-control-next');
        const indicatorBtn = e.target.closest('.carousel-indicators [data-bs-slide-to]');
        if (!prev && !next && !indicatorBtn) return;

        // Chỉ khi click đúng nút / chấm — không bắt cả vùng mép
        const hit = prev || next || indicatorBtn;
        if (hit !== e.target && !hit.contains(e.target)) return;

        // Chỉ chuyển slide trong bài — không mở lightbox / không điều hướng
        e.preventDefault();
        e.stopPropagation();
        if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();

        const carouselEl = hit.closest('.carousel');
        if (!carouselEl) return;
        const instance = getCarouselInstance(carouselEl);
        if (!instance) return;

        // Tạm dừng video hiện tại trước khi chuyển
        carouselEl.querySelectorAll('video').forEach((v) => {
            try { v.pause(); } catch (_) {}
        });

        if (indicatorBtn) {
            const idx = parseInt(indicatorBtn.getAttribute('data-bs-slide-to'), 10);
            if (!Number.isNaN(idx)) instance.to(idx);
            return;
        }
        if (prev) instance.prev();
        else instance.next();
    }

    function handleMediaClick(e) {
        // Ưu tiên nút mũi tên / dots → chỉ next/prev
        if (
            e.target.closest('.carousel-control-prev') ||
            e.target.closest('.carousel-control-next') ||
            e.target.closest('.carousel-indicators')
        ) {
            return;
        }

        if (isInteractiveChrome(e.target)) return;

        const img = e.target.closest('.carousel-item img');
        const video = e.target.closest('.carousel-item video, video.feed-video');
        const mediaEl = img || video;
        if (!mediaEl) {
            const commentImg = e.target.closest('.comment-image, .comment-preview-thumb');
            if (commentImg && commentImg.tagName === 'IMG') {
                e.preventDefault();
                e.stopPropagation();
                open([{ type: 'image', src: cleanUrl(commentImg.currentSrc || commentImg.src) }], 0);
            }
            return;
        }

        const carousel = mediaEl.closest('.carousel');
        if (!carousel) return;

        if (video) {
            const rect = video.getBoundingClientRect();
            if (e.clientY > rect.bottom - 56) return;
        }

        e.preventDefault();
        e.stopPropagation();

        const { items, index } = collectFromCarousel(carousel, mediaEl);
        open(items, index);
    }

    function ensureFeedVideoSettingsButton(video) {
        const slide = video.closest('.carousel-item');
        if (!slide || slide.querySelector('.hoshi-video-settings-btn')) return;
        slide.classList.add('hoshi-media-slide');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'hoshi-video-settings-btn';
        btn.title = 'Cấu hình video';
        btn.setAttribute('aria-label', 'Cấu hình video');
        btn.innerHTML = '<i class="fas fa-cog"></i>';
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const carousel = video.closest('.carousel');
            if (!carousel) return;
            const { items, index } = collectFromCarousel(carousel, video);
            open(items, index);
            // Mở luôn panel cấu hình sau khi lightbox sẵn sàng
            setTimeout(() => {
                if (state.items[state.index] && state.items[state.index].type === 'video') {
                    openSettings();
                }
            }, 0);
        });
        slide.appendChild(btn);
        video.loop = !!state.prefs.loop;
    }

    function scanFeedVideos(scope) {
        (scope || document).querySelectorAll('.carousel-item video, video.feed-video').forEach((video) => {
            ensureFeedVideoSettingsButton(video);
        });
    }

    document.addEventListener('click', handleCarouselNavClick, true);
    document.addEventListener('click', handleMediaClick, true);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => scanFeedVideos(document));
    } else {
        scanFeedVideos(document);
    }

    const mo = new MutationObserver((mutations) => {
        mutations.forEach((m) => {
            m.addedNodes.forEach((node) => {
                if (node.nodeType !== 1) return;
                if (node.matches && (node.matches('video') || node.querySelector('video'))) {
                    scanFeedVideos(node);
                }
            });
        });
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });

    window.HoshiMediaLightbox = {
        open,
        close,
        openFromElement(el) {
            const carousel = el && el.closest && el.closest('.carousel');
            if (carousel) {
                const { items, index } = collectFromCarousel(carousel, el);
                open(items, index);
            }
        },
        getPrefs: () => ({ ...state.prefs }),
        setPrefs( partial ) {
            state.prefs = { ...state.prefs, ...partial };
            savePrefs();
            applyVideoPrefs();
            applyFeedVideoPrefs();
        },
    };
})();
