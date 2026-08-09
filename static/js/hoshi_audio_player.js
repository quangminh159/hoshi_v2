/**
 * Hoshi audio player — UI thống nhất cho bài viết + bình luận.
 * - Tua / âm lượng / mute
 * - Chỉ phát 1 track tại một thời điểm
 * - Sửa WebM duration = Infinity (MediaRecorder)
 */
(function () {
    const SELECTOR = 'audio.post-audio, audio.comment-audio, audio.hoshi-audio';
    const PLAYING_CLASS = 'is-playing';

    function formatTime(seconds) {
        if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
        const total = Math.floor(seconds);
        const h = Math.floor(total / 3600);
        const m = Math.floor((total % 3600) / 60);
        const s = total % 60;
        if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function fixWebmDuration(audio) {
        return new Promise((resolve) => {
            const finish = () => resolve(
                Number.isFinite(audio.duration) && audio.duration !== Infinity ? audio.duration : 0
            );

            const tryFix = () => {
                if (Number.isFinite(audio.duration) && audio.duration > 0 && audio.duration !== Infinity) {
                    finish();
                    return;
                }
                const onTimeUpdate = () => {
                    audio.removeEventListener('timeupdate', onTimeUpdate);
                    try { audio.currentTime = 0; } catch (_) { /* ignore */ }
                    finish();
                };
                audio.addEventListener('timeupdate', onTimeUpdate);
                try {
                    audio.currentTime = 1e101;
                } catch (_) {
                    audio.removeEventListener('timeupdate', onTimeUpdate);
                    finish();
                }
            };

            if (audio.readyState >= 1) tryFix();
            else audio.addEventListener('loadedmetadata', tryFix, { once: true });
            setTimeout(finish, 2500);
        });
    }

    function pauseOthers(except) {
        document.querySelectorAll('audio.hoshi-audio-el').forEach((other) => {
            if (other !== except && !other.paused) other.pause();
        });
    }

    function buildShell() {
        const shell = document.createElement('div');
        shell.className = 'hoshi-audio-ui';
        shell.innerHTML = `
            <button type="button" class="hoshi-audio-toggle" aria-label="Phát">
                <i class="fas fa-play" aria-hidden="true"></i>
            </button>
            <div class="hoshi-audio-main">
                <div class="hoshi-audio-times">
                    <span class="hoshi-audio-current">0:00</span>
                    <span class="hoshi-audio-sep">/</span>
                    <span class="hoshi-audio-total">0:00</span>
                </div>
                <div class="hoshi-audio-seek-wrap">
                    <input type="range" class="hoshi-audio-seek" min="0" max="0" value="0" step="any" aria-label="Tua">
                </div>
            </div>
            <div class="hoshi-audio-volume-wrap">
                <button type="button" class="hoshi-audio-mute" aria-label="Tắt tiếng">
                    <i class="fas fa-volume-up" aria-hidden="true"></i>
                </button>
                <input type="range" class="hoshi-audio-volume" min="0" max="1" step="0.01" value="1" aria-label="Âm lượng">
            </div>
        `;
        return shell;
    }

    function updateSeekFill(seek) {
        const max = parseFloat(seek.max) || 0;
        const val = parseFloat(seek.value) || 0;
        const pct = max > 0 ? Math.min(100, Math.max(0, (val / max) * 100)) : 0;
        seek.style.setProperty('--seek-pct', `${pct}%`);
    }

    function updateVolumeFill(volume) {
        const val = parseFloat(volume.value) || 0;
        volume.style.setProperty('--vol-pct', `${Math.min(100, Math.max(0, val * 100))}%`);
    }

    function enhanceAudio(audio) {
        if (!audio || audio.dataset.hoshiAudioEnhanced === '1') return;
        audio.dataset.hoshiAudioEnhanced = '1';

        audio.removeAttribute('controls');
        audio.controls = false;
        audio.preload = audio.preload || 'metadata';
        audio.setAttribute('playsinline', '');
        if (!Number.isFinite(audio.volume)) audio.volume = 1;

        const shell = buildShell();
        const toggleBtn = shell.querySelector('.hoshi-audio-toggle');
        const seek = shell.querySelector('.hoshi-audio-seek');
        const currentEl = shell.querySelector('.hoshi-audio-current');
        const totalEl = shell.querySelector('.hoshi-audio-total');
        const muteBtn = shell.querySelector('.hoshi-audio-mute');
        const volume = shell.querySelector('.hoshi-audio-volume');
        const icon = toggleBtn.querySelector('i');
        const muteIcon = muteBtn.querySelector('i');

        let seeking = false;
        let duration = 0;
        let lastVolume = audio.volume > 0 ? audio.volume : 1;

        const parent = audio.parentNode;
        if (!parent) return;
        parent.insertBefore(shell, audio);
        shell.appendChild(audio);
        audio.classList.add('hoshi-audio-el');

        function setPlaying(playing) {
            shell.classList.toggle(PLAYING_CLASS, playing);
            if (playing) {
                icon.className = 'fas fa-pause';
                toggleBtn.setAttribute('aria-label', 'Tạm dừng');
            } else {
                icon.className = 'fas fa-play';
                toggleBtn.setAttribute('aria-label', 'Phát');
            }
        }

        function syncVolumeUI() {
            const v = audio.muted ? 0 : (Number.isFinite(audio.volume) ? audio.volume : 1);
            volume.value = String(v);
            updateVolumeFill(volume);
            if (audio.muted || v <= 0.001) {
                muteIcon.className = 'fas fa-volume-mute';
                muteBtn.setAttribute('aria-label', 'Bật tiếng');
            } else if (v < 0.45) {
                muteIcon.className = 'fas fa-volume-down';
                muteBtn.setAttribute('aria-label', 'Tắt tiếng');
            } else {
                muteIcon.className = 'fas fa-volume-up';
                muteBtn.setAttribute('aria-label', 'Tắt tiếng');
            }
        }

        function syncSeekMax() {
            const d = audio.duration;
            if (Number.isFinite(d) && d > 0 && d !== Infinity) {
                duration = d;
                seek.max = String(d);
                totalEl.textContent = formatTime(d);
            }
            updateSeekFill(seek);
        }

        function syncFromAudio() {
            if (seeking) return;
            syncSeekMax();
            const t = audio.currentTime || 0;
            seek.value = String(t);
            currentEl.textContent = formatTime(t);
            updateSeekFill(seek);
        }

        function stopBubble(e) {
            e.stopPropagation();
        }

        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            stopBubble(e);
            if (audio.paused) {
                pauseOthers(audio);
                audio.play().catch(() => { /* ignore autoplay block */ });
            } else {
                audio.pause();
            }
        });

        muteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            stopBubble(e);
            if (audio.muted || audio.volume <= 0.001) {
                audio.muted = false;
                audio.volume = lastVolume > 0 ? lastVolume : 1;
            } else {
                lastVolume = audio.volume > 0 ? audio.volume : 1;
                audio.muted = true;
            }
            syncVolumeUI();
        });

        const volumeWrap = shell.querySelector('.hoshi-audio-volume-wrap');
        // Mobile/touch: chạm loa giữ thanh volume mở tạm
        muteBtn.addEventListener('pointerdown', (e) => {
            if (e.pointerType === 'touch') {
                stopBubble(e);
                volumeWrap.classList.add('is-open');
            }
        });
        document.addEventListener('pointerdown', (e) => {
            if (!volumeWrap.contains(e.target)) volumeWrap.classList.remove('is-open');
        });

        volume.addEventListener('pointerdown', stopBubble);
        volume.addEventListener('click', stopBubble);
        volume.addEventListener('input', (e) => {
            stopBubble(e);
            const v = parseFloat(volume.value);
            if (!Number.isFinite(v)) return;
            audio.muted = v <= 0.001;
            audio.volume = Math.max(0, Math.min(1, v));
            if (v > 0.001) lastVolume = audio.volume;
            syncVolumeUI();
        });

        seek.addEventListener('pointerdown', (e) => {
            stopBubble(e);
            seeking = true;
        });
        seek.addEventListener('pointerup', (e) => {
            stopBubble(e);
            seeking = false;
        });
        seek.addEventListener('click', stopBubble);
        seek.addEventListener('input', (e) => {
            stopBubble(e);
            const t = parseFloat(seek.value) || 0;
            currentEl.textContent = formatTime(t);
            updateSeekFill(seek);
            if (Number.isFinite(t)) {
                try { audio.currentTime = t; } catch (_) { /* ignore */ }
            }
        });
        seek.addEventListener('change', (e) => {
            stopBubble(e);
            seeking = false;
            const t = parseFloat(seek.value) || 0;
            try { audio.currentTime = t; } catch (_) { /* ignore */ }
            syncFromAudio();
        });

        audio.addEventListener('play', () => {
            pauseOthers(audio);
            setPlaying(true);
        });
        audio.addEventListener('pause', () => setPlaying(false));
        audio.addEventListener('ended', () => {
            setPlaying(false);
            try { audio.currentTime = 0; } catch (_) { /* ignore */ }
            seek.value = '0';
            currentEl.textContent = '0:00';
            updateSeekFill(seek);
        });
        audio.addEventListener('timeupdate', syncFromAudio);
        audio.addEventListener('durationchange', syncSeekMax);
        audio.addEventListener('loadedmetadata', syncSeekMax);
        audio.addEventListener('volumechange', syncVolumeUI);

        shell.addEventListener('click', stopBubble);
        shell.addEventListener('pointerdown', stopBubble);

        const wrap = shell.closest('.post-audio-player, .comment-audio-player, .comment-audio-wrap');
        if (wrap && wrap.dataset.hoshiAudioBound !== '1') {
            wrap.dataset.hoshiAudioBound = '1';
            wrap.addEventListener('click', stopBubble);
            wrap.addEventListener('pointerdown', stopBubble);
        }

        volume.value = String(audio.volume);
        syncVolumeUI();
        syncFromAudio();

        const src = audio.currentSrc || audio.src || '';
        const looksWebm = /\.webm(\?|$)/i.test(src);
        if (looksWebm || !Number.isFinite(audio.duration) || audio.duration === Infinity) {
            fixWebmDuration(audio).then(() => {
                syncSeekMax();
                syncFromAudio();
            });
        }
    }

    window.initHoshiAudioPlayers = function (scope) {
        const root = scope || document;
        root.querySelectorAll(SELECTOR).forEach(enhanceAudio);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.initHoshiAudioPlayers(document));
    } else {
        window.initHoshiAudioPlayers(document);
    }
})();
