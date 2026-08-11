/**
 * Gọi thoại/video 1-1 (WebRTC P2P) — signaling qua WS chat / inbox.
 */
(function (window) {
    'use strict';

    const DEFAULT_ICE_SERVERS = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            {
                urls: [
                    'turn:openrelay.metered.ca:80',
                    'turn:openrelay.metered.ca:443',
                    'turns:openrelay.metered.ca:443',
                ],
                username: 'openrelayproject',
                credential: 'openrelayproject',
            },
        ],
    };

    let cachedIceConfig = null;
    let cachedIceAt = 0;
    const ICE_CACHE_MS = 5 * 60 * 1000;

    async function loadIceServers() {
        const now = Date.now();
        if (cachedIceConfig && (now - cachedIceAt) < ICE_CACHE_MS) {
            return cachedIceConfig;
        }
        try {
            const resp = await fetch('/chat/api/ice-servers/', {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data && Array.isArray(data.iceServers) && data.iceServers.length) {
                    cachedIceConfig = { iceServers: data.iceServers };
                    cachedIceAt = now;
                    return cachedIceConfig;
                }
            }
        } catch (err) {
            console.warn('[HoshiCall] ice-servers fetch failed', err);
        }
        cachedIceConfig = DEFAULT_ICE_SERVERS;
        cachedIceAt = now;
        return cachedIceConfig;
    }

    const RING_TIMEOUT_MS = 45000;
    const IS_CALL_POPUP = !!window.HOSHI_CALL_POPUP;
    const CALL_POPUP_NAME = 'hoshi_call_win';
    const PENDING_CALL_KEY = 'hoshi_pending_call';
    const CALL_CHANNEL_NAME = 'hoshi-call-bus';
    const CALL_WINDOW_PATH = window.HOSHI_CALL_WINDOW_URL || '/chat/call/';

    let callPopupRef = null;
    let callBus = null;
    try {
        callBus = new BroadcastChannel(CALL_CHANNEL_NAME);
    } catch (_) {
        callBus = null;
    }

    const state = {
        status: 'idle', // idle | outgoing | incoming | connecting | active | handoff
        callId: null,
        callMode: 'voice', // voice | video (ý định ban đầu / đang có video trong cuộc gọi)
        remoteHasVideo: false,
        conversationId: null,
        isCaller: false,
        peer: null,
        localStream: null,
        remoteStream: null,
        socket: null,
        ownSocket: false,
        ringTimer: null,
        startedAt: null,
        timerInterval: null,
        muted: false,
        cameraOff: false,
        pendingCandidates: [],
        remoteUser: null,
        writeSystemPending: false,
        minimized: false,
        handoffTimer: null,
        disconnectTimer: null,
    };

    function $(id) {
        return document.getElementById(id);
    }

    function uuid() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
        return `call-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    function currentUserId() {
        return Number(document.body?.dataset?.userId || 0);
    }

    function wsUrlForConversation(conversationId) {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        return `${protocol}${window.location.host}/ws/chat/${conversationId}/`;
    }

    function ensureOverlay() {
        let root = $('hoshiCallOverlay');
        if (root) return root;

        root = document.createElement('div');
        root.id = 'hoshiCallOverlay';
        root.className = 'hoshi-call-overlay';
        root.hidden = true;
        root.innerHTML = `
          <div class="hoshi-call-stage">
            <video id="hoshiCallRemoteVideo" class="hoshi-call-remote" autoplay playsinline></video>
            <audio id="hoshiCallRemoteAudio" class="hoshi-call-remote-audio" autoplay playsinline></audio>
            <video id="hoshiCallLocalVideo" class="hoshi-call-local" autoplay playsinline muted></video>
            <div class="hoshi-call-voice-panel" id="hoshiCallVoicePanel">
              <img id="hoshiCallAvatar" class="hoshi-call-avatar" src="/static/img/default-avatar.png" alt="">
              <div class="hoshi-call-name" id="hoshiCallName">—</div>
              <div class="hoshi-call-status" id="hoshiCallStatus">Đang gọi...</div>
              <div class="hoshi-call-timer" id="hoshiCallTimer" hidden>0:00</div>
            </div>
            <div class="hoshi-call-controls" id="hoshiCallControls">
              <button type="button" class="hoshi-call-btn" id="hoshiCallMinimizeBtn" title="Thu nhỏ để dùng app" hidden>
                <i class="fas fa-compress-alt"></i>
              </button>
              <button type="button" class="hoshi-call-btn" id="hoshiCallMuteBtn" title="Tắt mic">
                <i class="fas fa-microphone"></i>
              </button>
              <button type="button" class="hoshi-call-btn" id="hoshiCallCamBtn" title="Tắt camera" hidden>
                <i class="fas fa-video"></i>
              </button>
              <button type="button" class="hoshi-call-btn hoshi-call-btn--danger" id="hoshiCallHangupBtn" title="Kết thúc">
                <i class="fas fa-phone-slash"></i>
              </button>
              <button type="button" class="hoshi-call-btn hoshi-call-btn--success" id="hoshiCallAcceptBtn" title="Trả lời" hidden>
                <i class="fas fa-phone"></i>
              </button>
              <button type="button" class="hoshi-call-btn hoshi-call-btn--danger" id="hoshiCallRejectBtn" title="Từ chối" hidden>
                <i class="fas fa-phone-slash"></i>
              </button>
            </div>
            <div class="hoshi-call-mini" id="hoshiCallMini" hidden>
              <button type="button" class="hoshi-call-mini__main" id="hoshiCallMiniExpand" title="Mở rộng cuộc gọi">
                <img id="hoshiCallMiniAvatar" class="hoshi-call-mini__avatar" src="/static/img/default-avatar.png" alt="">
                <span class="hoshi-call-mini__meta">
                  <span class="hoshi-call-mini__name" id="hoshiCallMiniName">—</span>
                  <span class="hoshi-call-mini__timer" id="hoshiCallMiniTimer">Đang gọi</span>
                </span>
              </button>
              <button type="button" class="hoshi-call-mini__btn" id="hoshiCallMiniMute" title="Tắt/bật mic">
                <i class="fas fa-microphone"></i>
              </button>
              <button type="button" class="hoshi-call-mini__btn hoshi-call-mini__btn--danger" id="hoshiCallMiniHangup" title="Kết thúc">
                <i class="fas fa-phone-slash"></i>
              </button>
            </div>
          </div>
        `;
        document.body.appendChild(root);

        $('hoshiCallMuteBtn')?.addEventListener('click', toggleMute);
        $('hoshiCallCamBtn')?.addEventListener('click', onCamButtonClick);
        $('hoshiCallHangupBtn')?.addEventListener('click', hangupFromUi);
        $('hoshiCallAcceptBtn')?.addEventListener('click', acceptIncoming);
        $('hoshiCallRejectBtn')?.addEventListener('click', () => rejectIncoming('reject'));
        $('hoshiCallMinimizeBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            setMinimized(true);
        });
        $('hoshiCallMiniMute')?.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMute();
        });
        $('hoshiCallMiniHangup')?.addEventListener('click', (e) => {
            e.stopPropagation();
            hangupFromUi();
        });
        initMiniDrag(root);

        return root;
    }

    const MINI_POS_KEY = 'hoshi_call_mini_pos';
    const miniDrag = {
        active: false,
        moved: false,
        startX: 0,
        startY: 0,
        origLeft: 0,
        origTop: 0,
        pointerId: null,
    };

    function clampMiniPosition(root, left, top) {
        const margin = 8;
        const w = root.offsetWidth || 160;
        const h = root.offsetHeight || 56;
        const maxL = Math.max(margin, window.innerWidth - w - margin);
        const maxT = Math.max(margin, window.innerHeight - h - margin);
        return {
            left: Math.max(margin, Math.min(left, maxL)),
            top: Math.max(margin, Math.min(top, maxT)),
        };
    }

    function applyMiniPosition(root, left, top) {
        const pos = clampMiniPosition(root, left, top);
        root.style.left = `${pos.left}px`;
        root.style.top = `${pos.top}px`;
        root.style.right = 'auto';
        root.style.bottom = 'auto';
        try {
            sessionStorage.setItem(MINI_POS_KEY, JSON.stringify(pos));
        } catch (_) { /* ignore */ }
        return pos;
    }

    function clearMiniPositionStyles(root) {
        if (!root) return;
        root.style.left = '';
        root.style.top = '';
        root.style.right = '';
        root.style.bottom = '';
        root.classList.remove('is-dragging');
    }

    function restoreMiniPosition(root) {
        if (!root || !state.minimized) return;
        let saved = null;
        try {
            saved = JSON.parse(sessionStorage.getItem(MINI_POS_KEY) || 'null');
        } catch (_) {
            saved = null;
        }
        requestAnimationFrame(() => {
            if (!state.minimized || !root.classList.contains('is-minimized')) return;
            if (saved && typeof saved.left === 'number' && typeof saved.top === 'number') {
                applyMiniPosition(root, saved.left, saved.top);
            }
        });
    }

    function initMiniDrag(root) {
        if (!root || root.dataset.miniDragBound === '1') return;
        root.dataset.miniDragBound = '1';

        root.addEventListener('pointerdown', (e) => {
            if (!state.minimized) return;
            if (e.target.closest('.hoshi-call-mini__btn')) return;
            if (e.pointerType === 'mouse' && e.button !== 0) return;

            const rect = root.getBoundingClientRect();
            miniDrag.active = true;
            miniDrag.moved = false;
            miniDrag.startX = e.clientX;
            miniDrag.startY = e.clientY;
            miniDrag.origLeft = rect.left;
            miniDrag.origTop = rect.top;
            miniDrag.pointerId = e.pointerId;
            try { root.setPointerCapture(e.pointerId); } catch (_) { /* ignore */ }
        });

        root.addEventListener('pointermove', (e) => {
            if (!miniDrag.active || !state.minimized) return;
            const dx = e.clientX - miniDrag.startX;
            const dy = e.clientY - miniDrag.startY;
            if (!miniDrag.moved && (Math.abs(dx) > 8 || Math.abs(dy) > 8)) {
                miniDrag.moved = true;
                root.classList.add('is-dragging');
            }
            if (!miniDrag.moved) return;
            e.preventDefault();
            applyMiniPosition(root, miniDrag.origLeft + dx, miniDrag.origTop + dy);
        });

        const endDrag = () => {
            if (!miniDrag.active) return;
            miniDrag.active = false;
            root.classList.remove('is-dragging');
            try {
                if (miniDrag.pointerId != null) root.releasePointerCapture(miniDrag.pointerId);
            } catch (_) { /* ignore */ }
            miniDrag.pointerId = null;
        };

        root.addEventListener('pointerup', endDrag);
        root.addEventListener('pointercancel', endDrag);

        $('hoshiCallMiniExpand')?.addEventListener('click', (e) => {
            if (miniDrag.moved) {
                e.preventDefault();
                e.stopPropagation();
                miniDrag.moved = false;
                return;
            }
            setMinimized(false);
        });

        window.addEventListener('resize', () => {
            if (!state.minimized) return;
            const r = $('hoshiCallOverlay');
            if (!r || !r.style.left) return;
            const left = parseFloat(r.style.left) || 0;
            const top = parseFloat(r.style.top) || 0;
            applyMiniPosition(r, left, top);
        });
    }

    function setMinimized(on) {
        if (on && (state.status === 'idle' || state.status === 'incoming')) return;
        state.minimized = !!on;
        const root = ensureOverlay();
        root.classList.toggle('is-minimized', state.minimized);
        document.body.classList.toggle('hoshi-call-minimized', state.minimized);
        const mini = $('hoshiCallMini');
        if (mini) mini.hidden = !state.minimized;
        if (state.minimized) {
            restoreMiniPosition(root);
        } else {
            clearMiniPositionStyles(root);
            miniDrag.active = false;
            miniDrag.moved = false;
        }
        syncMiniUi();
        // Giữ media khi thu nhỏ
        if (state.remoteStream) {
            attachRemoteStream(state.remoteStream);
        }
        if (hasLocalVideoTrack()) {
            attachLocalPreview();
        }
    }

    function syncMiniUi() {
        const root = $('hoshiCallOverlay');
        const showVideo = !!(state.remoteHasVideo || (hasLocalVideoTrack() && !state.cameraOff));
        if (root) {
            root.classList.toggle('is-mini-video', state.minimized && showVideo);
        }

        const name = state.remoteUser?.username || 'Cuộc gọi';
        const avatar = state.remoteUser?.avatar_url || '/static/img/default-avatar.png';
        const nameEl = $('hoshiCallMiniName');
        const avatarEl = $('hoshiCallMiniAvatar');
        const timerEl = $('hoshiCallMiniTimer');
        if (nameEl) nameEl.textContent = name;
        if (avatarEl) {
            avatarEl.src = avatar;
            avatarEl.hidden = state.minimized && showVideo && !!state.remoteHasVideo;
        }
        if (timerEl) {
            if (state.status === 'active' && state.startedAt) {
                timerEl.textContent = formatDuration(getDurationSec());
            } else if (state.status === 'outgoing' || state.status === 'connecting') {
                timerEl.textContent = 'Đang gọi...';
            } else {
                timerEl.textContent = 'Trong cuộc gọi';
            }
        }
        const muteBtn = $('hoshiCallMiniMute');
        if (muteBtn) {
            muteBtn.classList.toggle('is-off', !!state.muted);
            muteBtn.innerHTML = state.muted
                ? '<i class="fas fa-microphone-slash"></i>'
                : '<i class="fas fa-microphone"></i>';
            muteBtn.title = state.muted ? 'Bật mic' : 'Tắt mic';
        }

        // Video trong bóng thu nhỏ: hiện remote (và local PiP nhỏ)
        const remote = $('hoshiCallRemoteVideo');
        if (remote && state.minimized) {
            if (state.remoteStream && state.remoteHasVideo) {
                remote.srcObject = state.remoteStream;
                remote.hidden = false;
                remote.play?.().catch(() => {});
            } else {
                remote.hidden = true;
            }
        }
        const local = $('hoshiCallLocalVideo');
        if (local && state.minimized) {
            if (hasLocalVideoTrack() && !state.cameraOff && state.localStream) {
                local.srcObject = state.localStream;
                local.hidden = false;
                local.play?.().catch(() => {});
            } else {
                local.hidden = true;
            }
        }
    }

    function setStatusText(text) {
        const el = $('hoshiCallStatus');
        if (el) el.textContent = text;
    }

    function formatDuration(sec) {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function startTimer() {
        stopTimer();
        state.startedAt = Date.now();
        const timerEl = $('hoshiCallTimer');
        if (timerEl) {
            timerEl.hidden = false;
            timerEl.textContent = '0:00';
        }
        state.timerInterval = setInterval(() => {
            const sec = Math.floor((Date.now() - state.startedAt) / 1000);
            const text = formatDuration(sec);
            if (timerEl) timerEl.textContent = text;
            const miniTimer = $('hoshiCallMiniTimer');
            if (miniTimer && state.minimized) miniTimer.textContent = text;
        }, 1000);
    }

    function stopTimer() {
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
    }

    function getDurationSec() {
        if (!state.startedAt) return 0;
        return Math.max(0, Math.floor((Date.now() - state.startedAt) / 1000));
    }

    function showOverlay({ incoming } = {}) {
        const root = ensureOverlay();
        root.hidden = false;
        // Cuộc gọi đến luôn hiện full; không thu nhỏ khi đang đổ chuông
        if (incoming) setMinimized(false);
        syncVideoUiClasses();
        root.classList.toggle('is-incoming', !!incoming);
        root.classList.toggle('is-active', state.status === 'active' || state.status === 'connecting' || state.status === 'outgoing');

        const name = state.remoteUser?.username || 'Người dùng';
        const avatar = state.remoteUser?.avatar_url || '/static/img/default-avatar.png';
        const nameEl = $('hoshiCallName');
        const avatarEl = $('hoshiCallAvatar');
        if (nameEl) nameEl.textContent = name;
        if (avatarEl) avatarEl.src = avatar;
        syncMiniUi();
        syncCallControls(!!incoming);
    }

    function setBtnVisible(el, visible) {
        if (!el) return;
        el.hidden = !visible;
        el.style.display = visible ? '' : 'none';
        el.setAttribute('aria-hidden', visible ? 'false' : 'true');
    }

    function syncCallControls(incoming) {
        const isIncoming = incoming === true || state.status === 'incoming';
        const accept = $('hoshiCallAcceptBtn');
        const reject = $('hoshiCallRejectBtn');
        const hangup = $('hoshiCallHangupBtn');
        const mute = $('hoshiCallMuteBtn');
        const cam = $('hoshiCallCamBtn');
        const minimize = $('hoshiCallMinimizeBtn');

        if (isIncoming) {
            setBtnVisible(accept, true);
            setBtnVisible(reject, true);
            setBtnVisible(hangup, false);
            setBtnVisible(mute, false);
            setBtnVisible(cam, false);
            setBtnVisible(minimize, false);
            setStatusText(state.callMode === 'video' ? 'Cuộc gọi video đến...' : 'Cuộc gọi thoại đến...');
            return;
        }

        // Đang gọi / kết nối / đổ chuông đi: mute + cúp + thu nhỏ; cam chỉ khi đã nối
        setBtnVisible(accept, false);
        setBtnVisible(reject, false);
        setBtnVisible(hangup, true);
        setBtnVisible(mute, true);
        setBtnVisible(cam, state.status === 'active' || state.status === 'connecting');
        setBtnVisible(minimize, !IS_CALL_POPUP);
        updateCamButton();
    }

    function hasLocalVideoTrack() {
        return !!(state.localStream && state.localStream.getVideoTracks().some((t) => t.readyState !== 'ended'));
    }

    function syncVideoUiClasses() {
        const root = $('hoshiCallOverlay');
        if (!root) return;
        const localOn = hasLocalVideoTrack() && !state.cameraOff;
        root.classList.toggle('has-remote-video', !!state.remoteHasVideo);
        root.classList.toggle('has-local-video', localOn);
        // is-video: có ít nhất một phía đang có video (để layout)
        root.classList.toggle('is-video', !!(state.remoteHasVideo || hasLocalVideoTrack()));
        // Chỉ ẩn name/status khi đã vào cuộc gọi thật (không phải lúc đổ chuông video)
        root.classList.toggle(
            'is-media-fullscreen',
            state.status === 'active' && (!!state.remoteHasVideo || localOn)
        );
    }

    function updateCamButton() {
        const cam = $('hoshiCallCamBtn');
        if (!cam) return;
        if (!hasLocalVideoTrack()) {
            cam.classList.remove('is-off');
            cam.title = 'Bật camera';
            cam.innerHTML = '<i class="fas fa-video"></i>';
            return;
        }
        cam.classList.toggle('is-off', state.cameraOff);
        cam.title = state.cameraOff ? 'Bật camera' : 'Tắt camera';
        cam.innerHTML = state.cameraOff
            ? '<i class="fas fa-video-slash"></i>'
            : '<i class="fas fa-video"></i>';
    }

    /** Chỉ cập nhật UI khi đối phương gửi video — KHÔNG bật cam local. */
    function onRemoteVideoAvailable() {
        state.remoteHasVideo = true;
        state.callMode = 'video';
        const root = $('hoshiCallOverlay');
        if (root && state.status === 'active') root.classList.add('is-active');
        syncVideoUiClasses();
        const remote = $('hoshiCallRemoteVideo');
        if (remote && state.remoteStream) {
            remote.srcObject = state.remoteStream;
            remote.hidden = false;
            remote.play?.().catch(() => {});
        }
        // Không gắn local preview nếu chưa tự bật cam
        const local = $('hoshiCallLocalVideo');
        if (local && !hasLocalVideoTrack()) {
            local.srcObject = null;
            local.hidden = true;
        }
        updateCamButton();
        if (state.minimized) syncMiniUi();
    }

    /** Sau khi CHÍNH MÌNH bật camera. */
    function onLocalVideoEnabled() {
        state.callMode = 'video';
        state.cameraOff = false;
        const root = $('hoshiCallOverlay');
        if (root && state.status === 'active') root.classList.add('is-active');
        syncVideoUiClasses();
        attachLocalPreview();
        updateCamButton();
        if (state.minimized) syncMiniUi();
    }

    function hideOverlay() {
        setMinimized(false);
        const root = $('hoshiCallOverlay');
        if (root) {
            clearMiniPositionStyles(root);
            root.hidden = true;
            root.classList.remove(
                'is-minimized',
                'is-incoming',
                'is-active',
                'is-media-fullscreen',
                'has-local-video',
                'has-remote-video',
                'is-video'
            );
        }
        document.body.classList.remove('hoshi-call-minimized');
        const remote = $('hoshiCallRemoteVideo');
        const remoteAudio = $('hoshiCallRemoteAudio');
        const local = $('hoshiCallLocalVideo');
        if (remote) remote.srcObject = null;
        if (remoteAudio) remoteAudio.srcObject = null;
        if (local) local.srcObject = null;
        const timerEl = $('hoshiCallTimer');
        if (timerEl) timerEl.hidden = true;
    }

    function sendSignal(type, extra = {}) {
        const payload = {
            type,
            call_id: state.callId,
            call_mode: state.callMode,
            ...extra,
        };
        const sock = state.socket;
        if (!sock || sock.readyState !== WebSocket.OPEN) {
            console.warn('[HoshiCall] socket not ready for', type);
            return false;
        }
        sock.send(JSON.stringify(payload));
        return true;
    }

    function clearRingTimer() {
        if (state.ringTimer) {
            clearTimeout(state.ringTimer);
            state.ringTimer = null;
        }
        stopRingtone();
    }

    /* ---- Nhạc chuông (Web Audio, không cần file) ---- */
    let ringCtx = null;
    let ringLoopTimer = null;
    let ringActiveOsc = [];

    function stopRingtone() {
        if (ringLoopTimer) {
            clearTimeout(ringLoopTimer);
            ringLoopTimer = null;
        }
        ringActiveOsc.forEach((node) => {
            try { node.stop(); } catch (_) { /* ignore */ }
            try { node.disconnect(); } catch (_) { /* ignore */ }
        });
        ringActiveOsc = [];
        if (ringCtx) {
            const ctx = ringCtx;
            ringCtx = null;
            try {
                if (ctx.state !== 'closed') ctx.close();
            } catch (_) { /* ignore */ }
        }
    }

    function scheduleDualTone(ctx, freqs, when, duration, volume) {
        const master = ctx.createGain();
        master.gain.value = 0;
        master.connect(ctx.destination);
        master.gain.setValueAtTime(0, when);
        master.gain.linearRampToValueAtTime(volume, when + 0.03);
        master.gain.setValueAtTime(volume, when + Math.max(0.05, duration - 0.05));
        master.gain.linearRampToValueAtTime(0, when + duration);

        freqs.forEach((freq) => {
            const osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.value = freq;
            osc.connect(master);
            osc.start(when);
            osc.stop(when + duration + 0.02);
            ringActiveOsc.push(osc);
        });
    }

    /** Kick ngắn — thump bass */
    function scheduleKick(ctx, when, volume) {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(150, when);
        osc.frequency.exponentialRampToValueAtTime(42, when + 0.12);
        g.gain.setValueAtTime(0, when);
        g.gain.linearRampToValueAtTime(volume, when + 0.004);
        g.gain.exponentialRampToValueAtTime(0.0001, when + 0.22);
        osc.connect(g);
        g.connect(ctx.destination);
        osc.start(when);
        osc.stop(when + 0.24);
        ringActiveOsc.push(osc);
    }

    /** Snare/clap nhẹ bằng noise */
    function scheduleSnare(ctx, when, volume) {
        const frames = Math.floor(ctx.sampleRate * 0.08);
        const buffer = ctx.createBuffer(1, frames, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < frames; i += 1) {
            data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / frames, 2.2);
        }
        const src = ctx.createBufferSource();
        const g = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        src.buffer = buffer;
        filter.type = 'bandpass';
        filter.frequency.value = 1800;
        filter.Q.value = 0.7;
        g.gain.setValueAtTime(volume, when);
        g.gain.exponentialRampToValueAtTime(0.0001, when + 0.1);
        src.connect(filter);
        filter.connect(g);
        g.connect(ctx.destination);
        src.start(when);
        src.stop(when + 0.12);
        ringActiveOsc.push(src);
    }

    /** Hi-hat tick */
    function scheduleHat(ctx, when, volume, open) {
        const frames = Math.floor(ctx.sampleRate * (open ? 0.08 : 0.035));
        const buffer = ctx.createBuffer(1, frames, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < frames; i += 1) {
            data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / frames, open ? 1.4 : 3);
        }
        const src = ctx.createBufferSource();
        const g = ctx.createGain();
        const filter = ctx.createBiquadFilter();
        src.buffer = buffer;
        filter.type = 'highpass';
        filter.frequency.value = 7000;
        g.gain.setValueAtTime(volume, when);
        g.gain.exponentialRampToValueAtTime(0.0001, when + (open ? 0.09 : 0.04));
        src.connect(filter);
        filter.connect(g);
        g.connect(ctx.destination);
        src.start(when);
        src.stop(when + (open ? 0.1 : 0.05));
        ringActiveOsc.push(src);
    }

    /** Bass note ngắn */
    function scheduleBass(ctx, freq, when, duration, volume) {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.value = freq;
        g.gain.setValueAtTime(0, when);
        g.gain.linearRampToValueAtTime(volume, when + 0.01);
        g.gain.setValueAtTime(volume * 0.85, when + duration * 0.55);
        g.gain.exponentialRampToValueAtTime(0.0001, when + duration);
        osc.connect(g);
        g.connect(ctx.destination);
        osc.start(when);
        osc.stop(when + duration + 0.02);
        ringActiveOsc.push(osc);
    }

    /** Lead pluck (hook) */
    function schedulePluck(ctx, freq, when, duration, volume) {
        const master = ctx.createGain();
        master.connect(ctx.destination);
        master.gain.setValueAtTime(0, when);
        master.gain.linearRampToValueAtTime(volume, when + 0.008);
        master.gain.exponentialRampToValueAtTime(Math.max(0.0008, volume * 0.2), when + duration * 0.45);
        master.gain.exponentialRampToValueAtTime(0.0001, when + duration);

        [
            { type: 'sine', mul: 1, gain: 1 },
            { type: 'triangle', mul: 2, gain: 0.18 },
            { type: 'sine', mul: 3.01, gain: 0.06 },
        ].forEach((p) => {
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.type = p.type;
            osc.frequency.value = freq * p.mul;
            g.gain.value = p.gain;
            osc.connect(g);
            g.connect(master);
            osc.start(when);
            osc.stop(when + duration + 0.02);
            ringActiveOsc.push(osc);
        });
    }

    /**
     * Beat độc quyền Hoshi — loop 8 nhịp (~108 BPM)
     * Kick/snare/hat + bass + hook Sol–La–Si–Re–Mi–Sol
     */
    function playHoshiSignatureRing(ctx, t0, volume) {
        const beat = 60 / 108; // ~0.556s / beat
        const step = beat / 2; // 8th note grid

        // Drums: 2 thanh (8 beat)
        for (let i = 0; i < 8; i += 1) {
            const t = t0 + i * beat;
            scheduleKick(ctx, t, volume * 1.15);
            if (i % 2 === 1) scheduleSnare(ctx, t, volume * 0.55);
            // hi-hat 8th
            scheduleHat(ctx, t, volume * 0.22, false);
            scheduleHat(ctx, t + step, volume * 0.16, i === 3 || i === 7);
        }

        // Bass line (root movement)
        const bass = [
            { f: 98.00, at: 0, dur: beat * 0.9 },   // G2
            { f: 110.00, at: 2, dur: beat * 0.9 },  // A2
            { f: 123.47, at: 4, dur: beat * 0.9 },  // B2
            { f: 98.00, at: 6, dur: beat * 0.85 },  // G2
        ];
        bass.forEach((n) => {
            scheduleBass(ctx, n.f, t0 + n.at * beat, n.dur, volume * 0.7);
        });

        // Hook melody on the beat (signature)
        const hook = [
            { f: 392.00, at: 0.0, dur: 0.28 }, // G4
            { f: 440.00, at: 1.0, dur: 0.28 }, // A4
            { f: 493.88, at: 2.0, dur: 0.28 }, // B4
            { f: 587.33, at: 3.0, dur: 0.32 }, // D5
            { f: 659.25, at: 4.0, dur: 0.32 }, // E5
            { f: 783.99, at: 5.0, dur: 0.45 }, // G5
            { f: 659.25, at: 6.5, dur: 0.22 }, // E5
            { f: 587.33, at: 7.0, dur: 0.35 }, // D5
        ];
        hook.forEach((n) => {
            const when = t0 + n.at * beat;
            schedulePluck(ctx, n.f, when, n.dur, volume * 0.95);
            schedulePluck(ctx, n.f * 2, when + 0.015, n.dur * 0.7, volume * 0.2);
        });
    }

    function startRingtone(kind) {
        stopRingtone();
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;

        try {
            ringCtx = new AC();
        } catch (_) {
            return;
        }

        if (ringCtx.state === 'suspended') {
            ringCtx.resume().catch(() => {});
        }

        const isIncoming = kind === 'incoming';
        const loopMs = Math.round((60 / 108) * 8 * 1000); // 8 beat @ 108 BPM

        const playCycle = () => {
            if (!ringCtx) return;
            const t0 = ringCtx.currentTime + 0.02;
            if (isIncoming) {
                playHoshiSignatureRing(ringCtx, t0, 0.11);
                ringLoopTimer = setTimeout(playCycle, loopMs);
            } else {
                scheduleDualTone(ringCtx, [440, 480], t0, 1.6, 0.07);
                ringLoopTimer = setTimeout(playCycle, 4200);
            }
        };

        playCycle();
    }

    async function getMedia(mode) {
        const constraints = {
            audio: true,
            video: mode === 'video' ? { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } } : false,
        };
        return navigator.mediaDevices.getUserMedia(constraints);
    }

    function attachLocalPreview() {
        const local = $('hoshiCallLocalVideo');
        if (!local) return;
        if (hasLocalVideoTrack() && state.localStream) {
            local.srcObject = state.localStream;
            local.hidden = false;
        } else {
            local.srcObject = null;
            local.hidden = true;
        }
        syncVideoUiClasses();
    }

    function attachRemoteStream(stream) {
        state.remoteStream = stream;
        const remote = $('hoshiCallRemoteVideo');
        const remoteAudio = $('hoshiCallRemoteAudio');
        if (remote) {
            remote.srcObject = stream;
            remote.muted = false;
            remote.hidden = !state.remoteHasVideo;
            remote.play?.().catch(() => {});
        }
        // Audio riêng — luôn phát (video remote bị display:none khi gọi thoại)
        if (remoteAudio) {
            remoteAudio.srcObject = stream;
            remoteAudio.muted = false;
            remoteAudio.play?.().catch(() => {});
        }
        syncVideoUiClasses();
    }

    function setVideoTransceiversRecvOnlyIfNeeded() {
        if (!state.peer || hasLocalVideoTrack()) return;
        state.peer.getTransceivers().forEach((transceiver) => {
            const kind = transceiver.receiver?.track?.kind || transceiver.sender?.track?.kind;
            // Transceiver video từ offer đối phương: chỉ nhận, không gửi (tránh tự bật cam)
            if (kind === 'video' || (!kind && transceiver.direction === 'sendrecv')) {
                try {
                    if (transceiver.direction === 'sendrecv' || transceiver.direction === 'sendonly') {
                        transceiver.direction = 'recvonly';
                    }
                } catch (_) { /* ignore */ }
            }
        });
    }

    async function createPeer() {
        cleanupPeer(false);
        const iceConfig = await loadIceServers();
        const pc = new RTCPeerConnection(iceConfig);
        state.peer = pc;

        if (state.localStream) {
            state.localStream.getTracks().forEach((track) => {
                pc.addTrack(track, state.localStream);
            });
        }

        pc.onicecandidate = (event) => {
            if (event.candidate) {
                sendSignal('call_ice', { candidate: event.candidate.toJSON() });
            }
        };

        pc.ontrack = (event) => {
            if (!state.remoteStream) {
                state.remoteStream = (event.streams && event.streams[0]) || new MediaStream();
            }
            if (event.track && !state.remoteStream.getTracks().includes(event.track)) {
                state.remoteStream.addTrack(event.track);
            }
            if (event.track && event.track.kind === 'video') {
                state.remoteHasVideo = true;
                onRemoteVideoAvailable();
            }
            attachRemoteStream(state.remoteStream);
        };

        pc.onconnectionstatechange = () => {
            if (state.disconnectTimer) {
                clearTimeout(state.disconnectTimer);
                state.disconnectTimer = null;
            }
            if (pc.connectionState === 'connected') {
                state.status = 'active';
                showOverlay({ incoming: false });
                setStatusText('Đang trong cuộc gọi');
                if (!state.startedAt) startTimer();
                const root = $('hoshiCallOverlay');
                if (root) {
                    root.classList.add('is-active');
                    syncCallControls(false);
                    syncVideoUiClasses();
                }
            } else if (pc.connectionState === 'disconnected') {
                if (state.status === 'active' || state.status === 'connecting') {
                    setStatusText('Mất kết nối tạm thời...');
                    state.disconnectTimer = setTimeout(() => {
                        state.disconnectTimer = null;
                        if (!state.peer) return;
                        const st = state.peer.connectionState;
                        if (st === 'disconnected' || st === 'failed') {
                            endCall({ reason: 'ended', writeSystem: state.isCaller, silentRemote: false });
                        }
                    }, 10000);
                }
            } else if (pc.connectionState === 'failed') {
                if (state.status === 'active' || state.status === 'connecting') {
                    endCall({ reason: 'ended', writeSystem: state.isCaller, silentRemote: false });
                }
            }
        };

        return pc;
    }

    async function flushPendingCandidates() {
        if (!state.peer) return;
        const list = state.pendingCandidates.splice(0);
        for (const candidate of list) {
            try {
                await state.peer.addIceCandidate(candidate);
            } catch (err) {
                console.warn('[HoshiCall] addIceCandidate', err);
            }
        }
    }

    function cleanupPeer(stopMedia = true) {
        if (state.disconnectTimer) {
            clearTimeout(state.disconnectTimer);
            state.disconnectTimer = null;
        }
        if (state.peer) {
            try {
                state.peer.onicecandidate = null;
                state.peer.ontrack = null;
                state.peer.onconnectionstatechange = null;
                state.peer.close();
            } catch (_) { /* ignore */ }
            state.peer = null;
        }
        if (stopMedia && state.localStream) {
            state.localStream.getTracks().forEach((t) => t.stop());
            state.localStream = null;
        }
        state.remoteStream = null;
        state.pendingCandidates = [];
    }

    function closeOwnSocket() {
        if (state.ownSocket && state.socket) {
            try {
                state.socket.close();
            } catch (_) { /* ignore */ }
        }
        if (state.ownSocket) {
            state.socket = null;
            state.ownSocket = false;
        }
    }

    function resetState() {
        clearRingTimer();
        clearHandoffTimer();
        stopTimer();
        cleanupPeer(true);
        closeOwnSocket();
        hideOverlay();
        state.status = 'idle';
        state.callId = null;
        state.conversationId = null;
        state.isCaller = false;
        state.startedAt = null;
        state.muted = false;
        state.cameraOff = false;
        state.remoteHasVideo = false;
        state.remoteUser = null;
        state.writeSystemPending = false;
        state.minimized = false;
    }

    function ensureSocket(conversationId) {
        return new Promise((resolve, reject) => {
            if (window.hoshiChatSocket && window.hoshiChatSocket.readyState === WebSocket.OPEN
                && Number(window.hoshiChatConversationId) === Number(conversationId)) {
                state.socket = window.hoshiChatSocket;
                state.ownSocket = false;
                resolve(state.socket);
                return;
            }
            if (state.socket && state.socket.readyState === WebSocket.OPEN
                && Number(state.conversationId) === Number(conversationId)) {
                resolve(state.socket);
                return;
            }

            const sock = new WebSocket(wsUrlForConversation(conversationId));
            state.socket = sock;
            state.ownSocket = true;
            const timer = setTimeout(() => {
                reject(new Error('Không kết nối được máy chủ gọi.'));
            }, 8000);
            sock.addEventListener('open', () => {
                clearTimeout(timer);
                resolve(sock);
            });
            sock.addEventListener('error', () => {
                clearTimeout(timer);
                reject(new Error('Lỗi kết nối WebSocket.'));
            });
            sock.addEventListener('message', (event) => {
                let data;
                try {
                    data = JSON.parse(event.data);
                } catch (_) {
                    return;
                }
                handleSignal(data);
            });
        });
    }

    async function startCall({ conversationId, mode, remoteUser }) {
        // Tab chính: ưu tiên cửa sổ riêng; nếu bị chặn popup → gọi ngay trên trang
        if (!IS_CALL_POPUP) {
            const win = launchCallPopup({
                role: 'caller',
                conversationId,
                mode: mode === 'video' ? 'video' : 'voice',
                remoteUser,
            });
            if (win) {
                await wait(280);
                if (!win.closed) return win;
                callPopupRef = null;
            }
            showPopupBlockedHint();
            return startCallInPlace({ conversationId, mode, remoteUser });
        }

        return startCallInPlace({ conversationId, mode, remoteUser });
    }

    function wait(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function showPopupBlockedHint() {
        // Không chặn cuộc gọi — chỉ nhắc nhẹ 1 lần
        try {
            if (sessionStorage.getItem('hoshi_popup_hint') === '1') return;
            sessionStorage.setItem('hoshi_popup_hint', '1');
        } catch (_) { /* ignore */ }
        window.alert(
            'Trình duyệt đang chặn cửa sổ gọi.\n\n'
            + 'Cuộc gọi sẽ chạy trên trang này.\n'
            + 'Muốn gọi cửa sổ riêng: cho phép popup cho trang Moora (biểu tượng bị chặn trên thanh địa chỉ).'
        );
    }

    async function startCallInPlace({ conversationId, mode, remoteUser }) {
        if (state.status !== 'idle') {
            window.alert('Bạn đang trong một cuộc gọi khác.');
            return;
        }
        if (!navigator.mediaDevices?.getUserMedia) {
            window.alert('Trình duyệt không hỗ trợ gọi.');
            return;
        }

        state.callId = uuid();
        state.callMode = mode === 'video' ? 'video' : 'voice';
        state.conversationId = conversationId;
        state.isCaller = true;
        state.status = 'outgoing';
        state.remoteUser = remoteUser || null;

        try {
            state.localStream = await getMedia(state.callMode);
        } catch (err) {
            resetState();
            window.alert('Không thể truy cập micro/camera. Hãy cho phép quyền truy cập.');
            return;
        }

        showOverlay({ incoming: false });
        if (state.callMode === 'video') {
            onLocalVideoEnabled();
        } else {
            attachLocalPreview();
        }
        setStatusText('Đang đổ chuông...');
        notifyCallBus({ type: 'call_active' });
        startRingtone('outgoing');

        try {
            await ensureSocket(conversationId);
        } catch (err) {
            resetState();
            window.alert(err.message || 'Không kết nối được.');
            return;
        }

        sendSignal('call_invite', { call_mode: state.callMode });

        state.ringTimer = setTimeout(() => {
            endCall({ reason: 'timeout', writeSystem: true });
        }, RING_TIMEOUT_MS);
    }

    function getCallWindowUrl() {
        return CALL_WINDOW_PATH;
    }

    function launchCallPopup({ role, conversationId, mode, remoteUser, callId }) {
        if (callPopupRef && !callPopupRef.closed) {
            try { callPopupRef.focus(); } catch (_) { /* ignore */ }
            window.alert('Bạn đang có cửa sổ gọi đang mở.');
            return callPopupRef;
        }

        const params = new URLSearchParams();
        params.set('role', role || 'caller');
        params.set('conversation_id', String(conversationId || ''));
        params.set('mode', mode === 'video' ? 'video' : 'voice');
        if (callId) params.set('call_id', callId);
        if (remoteUser) {
            if (remoteUser.id != null) params.set('remote_id', String(remoteUser.id));
            if (remoteUser.username) params.set('remote_username', remoteUser.username);
            if (remoteUser.avatar_url) params.set('remote_avatar', remoteUser.avatar_url);
        }

        const url = `${getCallWindowUrl()}?${params.toString()}`;
        const features = 'popup=yes,width=400,height=700,resizable=yes,scrollbars=no,status=no';
        let win = null;
        try {
            win = window.open(url, CALL_POPUP_NAME, features);
        } catch (_) {
            win = null;
        }
        // Một số trình duyệt trả về window giả rồi đóng ngay
        if (!win || win.closed) {
            return null;
        }
        callPopupRef = win;
        try { win.focus(); } catch (_) { /* ignore */ }

        const poll = window.setInterval(() => {
            if (!callPopupRef || callPopupRef.closed) {
                window.clearInterval(poll);
                callPopupRef = null;
            }
        }, 1000);
        return win;
    }

    function notifyCallBus(msg) {
        try {
            callBus?.postMessage(msg);
        } catch (_) { /* ignore */ }
    }

    function remoteUserFromParams(params) {
        const id = params.get('remote_id');
        return {
            id: id ? Number(id) : null,
            username: params.get('remote_username') || 'Người dùng',
            avatar_url: params.get('remote_avatar') || '/static/img/default-avatar.png',
        };
    }

    function clearHandoffTimer() {
        if (state.handoffTimer) {
            clearTimeout(state.handoffTimer);
            state.handoffTimer = null;
        }
    }

    function finishHandoffToIdle() {
        if (state.status !== 'handoff') return;
        clearHandoffTimer();
        clearRingTimer();
        stopRingtone();
        hideOverlay();
        state.status = 'idle';
        state.callId = null;
        state.conversationId = null;
        state.remoteUser = null;
        state.isCaller = false;
    }

    /** Caller cúp / remote end trong lúc tab chính đang chuyển sang popup */
    function abortHandoffFromRemote(payload) {
        if (state.status !== 'handoff') return;
        const callId = state.callId;
        notifyCallBus({
            type: 'remote_hangup',
            call_id: callId,
            reason: (payload && payload.reason) || 'ended',
        });
        if (callPopupRef && !callPopupRef.closed) {
            try { callPopupRef.close(); } catch (_) { /* ignore */ }
        }
        callPopupRef = null;
        clearHandoffTimer();
        resetState();
    }

    async function bootPopup() {
        if (!IS_CALL_POPUP) return;
        ensureOverlay();
        const params = new URLSearchParams(window.location.search);
        const role = params.get('role') || 'caller';
        const conversationId = params.get('conversation_id');
        const mode = params.get('mode') === 'video' ? 'video' : 'voice';

        window.addEventListener('pagehide', () => {
            if (state.status !== 'idle') {
                leaveCallOnPageExit();
            }
        });

        if (callBus) {
            callBus.addEventListener('message', (event) => {
                const data = event.data || {};
                if (data.type === 'remote_hangup') {
                    if (data.call_id && state.callId && data.call_id !== state.callId) return;
                    if (state.status === 'idle') {
                        try { window.close(); } catch (_) { /* ignore */ }
                        return;
                    }
                    endCall({
                        reason: data.reason || 'ended',
                        writeSystem: false,
                        silentRemote: true,
                    });
                }
            });
        }

        if (role === 'caller') {
            if (!conversationId) {
                window.alert('Thiếu cuộc trò chuyện.');
                window.close();
                return;
            }
            await startCall({
                conversationId,
                mode,
                remoteUser: remoteUserFromParams(params),
            });
            return;
        }

        // Callee: sessionStorage trước, fallback query URL
        let pending = null;
        try {
            pending = JSON.parse(sessionStorage.getItem(PENDING_CALL_KEY) || 'null');
        } catch (_) {
            pending = null;
        }
        sessionStorage.removeItem(PENDING_CALL_KEY);

        if (!pending || !pending.call_id) {
            const callId = params.get('call_id');
            if (callId && conversationId) {
                pending = {
                    call_id: callId,
                    conversation_id: conversationId,
                    call_mode: mode,
                    from_user: remoteUserFromParams(params),
                };
            }
        }

        if (!pending || !pending.call_id) {
            window.alert('Không tìm thấy cuộc gọi đến.');
            window.close();
            return;
        }

        state.status = 'incoming';
        state.callId = pending.call_id;
        state.callMode = pending.call_mode === 'video' ? 'video' : 'voice';
        state.conversationId = pending.conversation_id || conversationId;
        state.isCaller = false;
        state.remoteUser = pending.from_user || remoteUserFromParams(params);
        notifyCallBus({ type: 'call_popup_ready', call_id: state.callId, role: 'callee' });
        notifyCallBus({ type: 'call_active' });
        await acceptIncomingInPlace();
    }

    async function onIncomingInvite(payload) {
        if (!payload || Number(payload.from_user?.id) === currentUserId()) return;

        const popupBusy = !!(callPopupRef && !callPopupRef.closed);
        if (state.status !== 'idle' || popupBusy || IS_CALL_POPUP) {
            // Đang bận — báo busy qua socket tạm, không đụng state cuộc gọi hiện tại
            try {
                const busySock = new WebSocket(wsUrlForConversation(payload.conversation_id));
                busySock.addEventListener('open', () => {
                    busySock.send(JSON.stringify({
                        type: 'call_busy',
                        call_id: payload.call_id,
                        call_mode: payload.call_mode || 'voice',
                    }));
                    setTimeout(() => {
                        try { busySock.close(); } catch (_) { /* ignore */ }
                    }, 300);
                });
            } catch (_) { /* ignore */ }
            return;
        }

        state.status = 'incoming';
        state.callId = payload.call_id;
        state.callMode = payload.call_mode === 'video' ? 'video' : 'voice';
        state.conversationId = payload.conversation_id;
        state.isCaller = false;
        state.remoteUser = payload.from_user || null;

        showOverlay({ incoming: true });
        setStatusText(state.callMode === 'video' ? 'Cuộc gọi video đến...' : 'Cuộc gọi thoại đến...');
        startRingtone('incoming');

        state.ringTimer = setTimeout(() => {
            rejectIncoming('timeout');
        }, RING_TIMEOUT_MS);
    }

    async function acceptIncoming() {
        if (state.status !== 'incoming') return;

        // Tab chính: chuyển cuộc gọi sang cửa sổ riêng (user gesture → không bị chặn popup)
        if (!IS_CALL_POPUP) {
            clearRingTimer();
            const pending = {
                call_id: state.callId,
                conversation_id: state.conversationId,
                call_mode: state.callMode,
                from_user: state.remoteUser,
            };
            try {
                sessionStorage.setItem(PENDING_CALL_KEY, JSON.stringify(pending));
            } catch (_) { /* ignore */ }

            const win = launchCallPopup({
                role: 'callee',
                conversationId: state.conversationId,
                mode: state.callMode,
                remoteUser: state.remoteUser,
                callId: state.callId,
            });
            if (!win) {
                sessionStorage.removeItem(PENDING_CALL_KEY);
                showPopupBlockedHint();
                await acceptIncomingInPlace();
                return;
            }
            await wait(280);
            if (win.closed) {
                callPopupRef = null;
                sessionStorage.removeItem(PENDING_CALL_KEY);
                showPopupBlockedHint();
                await acceptIncomingInPlace();
                return;
            }

            // Giữ callId trong handoff — vẫn nhận call_end cho đến khi popup ready
            stopRingtone();
            hideOverlay();
            state.status = 'handoff';
            clearHandoffTimer();
            state.handoffTimer = setTimeout(() => {
                // Popup mở nhưng chưa ack — vẫn coi đã chuyển (URL fallback đủ data)
                if (state.status === 'handoff' && callPopupRef && !callPopupRef.closed) {
                    finishHandoffToIdle();
                } else if (state.status === 'handoff') {
                    // Popup chết im — nhận lại trên trang
                    state.status = 'incoming';
                    showOverlay({ incoming: true });
                    setStatusText(state.callMode === 'video' ? 'Cuộc gọi video đến...' : 'Cuộc gọi thoại đến...');
                    startRingtone('incoming');
                    acceptIncomingInPlace();
                }
            }, 8000);
            return;
        }

        await acceptIncomingInPlace();
    }

    async function acceptIncomingInPlace() {
        if (state.status !== 'incoming') return;
        clearRingTimer();

        try {
            state.localStream = await getMedia(state.callMode);
        } catch (err) {
            rejectIncoming('reject');
            window.alert('Không thể truy cập micro/camera.');
            return;
        }

        try {
            await ensureSocket(state.conversationId);
        } catch (err) {
            resetState();
            window.alert(err.message || 'Không kết nối được.');
            return;
        }

        state.status = 'connecting';
        showOverlay({ incoming: false });
        if (state.callMode === 'video') {
            onLocalVideoEnabled();
        } else {
            attachLocalPreview();
        }
        setStatusText('Đang kết nối...');
        notifyCallBus({ type: 'call_active' });
        sendSignal('call_accept');
        await createPeer();
    }

    function rejectIncoming(reason) {
        if (state.status !== 'incoming' && state.status !== 'connecting') return;
        clearRingTimer();
        const writeSystem = reason === 'timeout';
        ensureSocket(state.conversationId).then(() => {
            // timeout → call_end + ghi "nhỡ"; reject → call_reject (caller ghi system)
            sendSignal(reason === 'timeout' ? 'call_end' : 'call_reject', {
                reason: reason || 'reject',
                write_system: writeSystem,
                duration: 0,
            });
            resetState();
        }).catch(() => resetState());
    }

    async function onAccepted() {
        if (!state.isCaller || state.status !== 'outgoing') return;
        clearRingTimer();
        state.status = 'connecting';
        setStatusText('Đang kết nối...');
        await createPeer();
        const offer = await state.peer.createOffer();
        await state.peer.setLocalDescription(offer);
        sendSignal('call_offer', { sdp: state.peer.localDescription });
    }

    async function onOffer(payload) {
        if (!state.peer) {
            if (state.status === 'idle') return;
            await createPeer();
        }

        if (payload.call_mode === 'video') {
            // Chỉ báo UI remote — không bật cam local
            state.remoteHasVideo = true;
            onRemoteVideoAvailable();
            setStatusText('Đối phương đã bật camera');
        }

        try {
            // Glare khi cả hai cùng nâng cấp video — phía "polite" (id lớn hơn) nhận offer
            if (state.peer.signalingState !== 'stable') {
                const remoteId = Number(state.remoteUser?.id || 0);
                const polite = currentUserId() > remoteId;
                if (!polite) return;
                await state.peer.setLocalDescription({ type: 'rollback' });
            }

            await state.peer.setRemoteDescription(payload.sdp);
            // Quan trọng: không gửi video nếu mình chưa bật cam (tránh trình duyệt tự xin camera)
            setVideoTransceiversRecvOnlyIfNeeded();
            await flushPendingCandidates();
            const answer = await state.peer.createAnswer();
            await state.peer.setLocalDescription(answer);
            sendSignal('call_answer', { sdp: state.peer.localDescription });

            if (state.status !== 'active') {
                state.status = 'connecting';
                setStatusText('Đang kết nối...');
            }
        } catch (err) {
            console.warn('[HoshiCall] onOffer', err);
        }
    }

    async function onAnswer(payload) {
        if (!state.peer) return;
        try {
            await state.peer.setRemoteDescription(payload.sdp);
            await flushPendingCandidates();
            if (payload.call_mode === 'video') {
                state.remoteHasVideo = true;
                onRemoteVideoAvailable();
            }
        } catch (err) {
            console.warn('[HoshiCall] onAnswer', err);
        }
    }

    async function onIce(payload) {
        if (!payload?.candidate) return;
        if (!state.peer || !state.peer.remoteDescription) {
            state.pendingCandidates.push(payload.candidate);
            return;
        }
        try {
            await state.peer.addIceCandidate(payload.candidate);
        } catch (err) {
            console.warn('[HoshiCall] ice', err);
        }
    }

    function hangupFromUi() {
        if (state.status === 'idle' || state.status === 'handoff') return;
        if (state.status === 'outgoing') {
            endCall({ reason: 'cancel', writeSystem: true });
            return;
        }
        if (state.status === 'incoming') {
            rejectIncoming('reject');
            return;
        }
        endCall({ reason: 'ended', writeSystem: true });
    }

    function leaveCallOnPageExit() {
        if (state.status === 'idle' || state.status === 'handoff') return;
        // Tab chính: cuộc gọi đang ở popup → không cúp
        if (!IS_CALL_POPUP && callPopupRef && !callPopupRef.closed) return;
        const ringingOut = state.status === 'outgoing';
        endCall({
            reason: ringingOut ? 'cancel' : 'ended',
            writeSystem: !!(state.isCaller || ringingOut),
            silentRemote: false,
        });
    }

    function endCall({ reason = 'ended', writeSystem = false, silentRemote = false } = {}) {
        if (state.status === 'idle') return;

        clearRingTimer();
        const duration = getDurationSec();
        const shouldWrite = writeSystem || (state.isCaller && ['timeout', 'cancel', 'missed'].includes(reason));

        if (!silentRemote && state.socket && state.socket.readyState === WebSocket.OPEN) {
            sendSignal('call_end', {
                reason,
                duration,
                write_system: !!shouldWrite,
            });
        }

        resetState();
        notifyCallBus({ type: 'call_ended', reason });

        if (IS_CALL_POPUP) {
            window.setTimeout(() => {
                try { window.close(); } catch (_) { /* ignore */ }
            }, 350);
        }
    }

    function toggleMute() {
        if (!state.localStream) return;
        state.muted = !state.muted;
        state.localStream.getAudioTracks().forEach((t) => {
            t.enabled = !state.muted;
        });
        const btn = $('hoshiCallMuteBtn');
        if (btn) {
            btn.classList.toggle('is-off', state.muted);
            btn.innerHTML = state.muted
                ? '<i class="fas fa-microphone-slash"></i>'
                : '<i class="fas fa-microphone"></i>';
            btn.title = state.muted ? 'Bật mic' : 'Tắt mic';
        }
        syncMiniUi();
    }

    async function onCamButtonClick() {
        if (state.status !== 'active' && state.status !== 'connecting') return;
        if (!hasLocalVideoTrack()) {
            await upgradeToVideo();
            return;
        }
        toggleCamera();
    }

    async function upgradeToVideo() {
        if (!state.peer) {
            window.alert('Cuộc gọi chưa sẵn sàng để bật camera.');
            return;
        }
        try {
            const videoOnly = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
            });
            const videoTrack = videoOnly.getVideoTracks()[0];
            if (!videoTrack) throw new Error('no-video-track');

            if (!state.localStream) {
                state.localStream = new MediaStream();
            }
            state.localStream.addTrack(videoTrack);
            state.peer.addTrack(videoTrack, state.localStream);

            onLocalVideoEnabled();
            setStatusText('Đã bật camera');

            sendSignal('call_mode', { call_mode: 'video' });
            const offer = await state.peer.createOffer();
            await state.peer.setLocalDescription(offer);
            sendSignal('call_offer', {
                sdp: state.peer.localDescription,
                call_mode: 'video',
            });
        } catch (err) {
            console.warn('[HoshiCall] upgradeToVideo', err);
            window.alert('Không bật được camera. Hãy cho phép quyền camera.');
        }
    }

    function toggleCamera() {
        if (!state.localStream || !hasLocalVideoTrack()) return;
        state.cameraOff = !state.cameraOff;
        state.localStream.getVideoTracks().forEach((t) => {
            t.enabled = !state.cameraOff;
        });
        updateCamButton();
        syncVideoUiClasses();
        attachLocalPreview();
        if (state.minimized) syncMiniUi();
    }

    function onRemoteModeChange(payload) {
        if (payload.call_mode === 'video') {
            state.remoteHasVideo = true;
            onRemoteVideoAvailable();
            setStatusText('Đối phương đã bật camera');
        }
    }

    function handleSignal(data) {
        if (!data) return;

        if (data.type === 'call_error') {
            const msg = data.message || 'Không thể thực hiện cuộc gọi.';
            if (state.status === 'outgoing' || state.status === 'connecting' || state.status === 'incoming') {
                window.alert(msg);
                resetState();
            }
            return;
        }

        if (!data.signal) {
            // raw types from socket without wrapper
            if (data?.type && String(data.type).startsWith('call_')) {
                data = { ...data, signal: data.type };
            } else {
                return;
            }
        }

        const signal = data.signal;
        if (!signal || !String(signal).startsWith('call_')) return;

        // Ignore echoes of our own signals if they somehow arrive
        if (data.from_user && Number(data.from_user.id) === currentUserId()) {
            return;
        }

        if (data.call_id && state.callId && data.call_id !== state.callId) {
            if (signal === 'call_invite') {
                // another call while busy handled in onIncomingInvite
            } else {
                return;
            }
        }

        // Tránh xử lý trùng invite (room + inbox)
        if (signal === 'call_invite' && state.callId && data.call_id === state.callId
            && (state.status === 'incoming' || state.status === 'connecting' || state.status === 'outgoing' || state.status === 'handoff')) {
            return;
        }

        switch (signal) {
            case 'call_invite':
                onIncomingInvite(data);
                break;
            case 'call_accept':
                onAccepted();
                break;
            case 'call_reject':
            case 'call_busy':
                if (state.status === 'handoff') {
                    abortHandoffFromRemote({ reason: signal === 'call_busy' ? 'busy' : 'reject' });
                    break;
                }
                if (state.isCaller) {
                    clearRingTimer();
                    const reason = signal === 'call_busy' ? 'busy' : 'reject';
                    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
                        sendSignal('call_end', {
                            reason,
                            duration: 0,
                            write_system: true,
                        });
                    }
                    resetState();
                }
                break;
            case 'call_offer':
                onOffer(data);
                break;
            case 'call_answer':
                onAnswer(data);
                break;
            case 'call_ice':
                onIce(data);
                break;
            case 'call_mode':
                onRemoteModeChange(data);
                break;
            case 'call_end':
                if (state.status === 'handoff') {
                    abortHandoffFromRemote(data);
                    break;
                }
                endCall({ reason: data.reason || 'ended', writeSystem: false, silentRemote: true });
                break;
            default:
                break;
        }
    }

    function bindChatSocket(socket, conversationId) {
        if (!socket) return;
        const prev = window.hoshiChatSocket;
        if (prev && prev !== socket) {
            try {
                if (prev.readyState === WebSocket.OPEN || prev.readyState === WebSocket.CONNECTING) {
                    prev.close();
                }
            } catch (_) { /* ignore */ }
        }
        window.hoshiChatSocket = socket;
        window.hoshiChatConversationId = conversationId;
        // Nếu đang gọi cùng conversation bằng socket riêng → chuyển sang socket trang chat
        if (state.conversationId && Number(state.conversationId) === Number(conversationId)) {
            if (state.ownSocket && state.socket && state.socket !== socket) {
                try { state.socket.close(); } catch (_) { /* ignore */ }
            }
            state.socket = socket;
            state.ownSocket = false;
        }
    }

    /* ---- Giữ cuộc gọi khi lướt trang (soft navigation) ---- */
    let softNavBusy = false;

    function sameOriginUrl(href) {
        try {
            return new URL(href, window.location.href);
        } catch (_) {
            return null;
        }
    }

    function softNavTargetFromAnchor(anchor) {
        if (!anchor || state.status === 'idle' || state.status === 'handoff') return null;
        if (anchor.target && anchor.target !== '_self') return null;
        if (anchor.hasAttribute('download')) return null;
        if (anchor.dataset.noSoftnav === '1') return null;
        const href = anchor.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) {
            return null;
        }
        const url = sameOriginUrl(href);
        if (!url || url.origin !== window.location.origin) return null;
        if (/\/(accounts\/logout|admin)(\/|$)/i.test(url.pathname)) return null;
        if (url.pathname === window.location.pathname
            && url.search === window.location.search
            && url.hash) {
            return null;
        }
        return url;
    }

    function loadScript(src) {
        return new Promise((resolve) => {
            const s = document.createElement('script');
            s.src = src;
            s.dataset.hoshiSoftnav = '1';
            s.onload = () => resolve();
            s.onerror = () => resolve();
            document.body.appendChild(s);
        });
    }

    async function softNavigate(url, { push = true } = {}) {
        if (softNavBusy || state.status === 'idle') return;
        softNavBusy = true;
        const abs = typeof url === 'string' ? url : url.href;
        try {
            setMinimized(true);
            const resp = await fetch(abs, {
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-Hoshi-SoftNav': '1',
                },
            });
            if (!resp.ok || (resp.redirected && /\/accounts\/login/i.test(resp.url))) {
                window.location.href = abs;
                return;
            }
            const html = await resp.text();
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const newMain = doc.querySelector('main.site-main');
            const curMain = document.querySelector('main.site-main');
            if (!newMain || !curMain) {
                window.location.href = abs;
                return;
            }

            document.querySelectorAll('[data-hoshi-softnav]').forEach((el) => el.remove());

            // Overlay gọi nằm ngoài <main> → không bị xóa
            curMain.innerHTML = newMain.innerHTML;

            document.title = doc.title || document.title;
            const keepClasses = ['user-authenticated', 'hoshi-call-minimized'];
            const kept = keepClasses.filter((c) => document.body.classList.contains(c));
            document.body.className = doc.body.className || '';
            kept.forEach((c) => document.body.classList.add(c));
            if (state.minimized) document.body.classList.add('hoshi-call-minimized');
            if (doc.body.dataset.userId) {
                document.body.dataset.userId = doc.body.dataset.userId;
            }

            doc.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
                const href = link.getAttribute('href');
                if (!href) return;
                const absHref = sameOriginUrl(href)?.href || href;
                const exists = [...document.querySelectorAll('link[rel="stylesheet"]')].some(
                    (l) => l.href === absHref || l.getAttribute('href') === href
                );
                if (exists) return;
                const el = document.createElement('link');
                el.rel = 'stylesheet';
                el.href = href;
                el.dataset.hoshiSoftnav = '1';
                document.head.appendChild(el);
            });

            const newMainEl = doc.querySelector('main.site-main');
            const pageScripts = [...doc.body.querySelectorAll('script')].filter(
                (s) => !newMainEl || !newMainEl.contains(s)
            );
            for (const old of pageScripts) {
                const src = old.getAttribute('src');
                if (src) {
                    const absSrc = sameOriginUrl(src)?.href || src;
                    if ([...document.scripts].some((s) => s.src === absSrc)) continue;
                    // Không load lại webrtc_call / core
                    if (/webrtc_call\.js/i.test(src)) continue;
                    await loadScript(src);
                } else if ((old.textContent || '').trim()) {
                    const s = document.createElement('script');
                    s.textContent = old.textContent;
                    s.dataset.hoshiSoftnav = '1';
                    document.body.appendChild(s);
                }
            }

            curMain.querySelectorAll('script').forEach((old) => {
                const s = document.createElement('script');
                if (old.src) s.src = old.src;
                else s.textContent = old.textContent;
                s.dataset.hoshiSoftnav = '1';
                old.replaceWith(s);
            });

            if (push) {
                history.pushState({ hoshiSoftNav: true }, '', abs);
            }

            window.scrollTo(0, 0);
            document.dispatchEvent(new CustomEvent('hoshi:softnav', { detail: { url: abs } }));

            // Feed đã có infinite_scroll sẵn → reload container nếu có
            if (document.getElementById('posts-container') && window.infiniteScroll?.resetAndReload) {
                try { window.infiniteScroll.resetAndReload(); } catch (_) { /* ignore */ }
            }
        } catch (err) {
            console.warn('[HoshiCall] softNavigate failed', err);
            window.location.href = abs;
        } finally {
            softNavBusy = false;
        }
    }

    document.addEventListener('click', (e) => {
        if (state.status === 'idle') return;
        if (e.defaultPrevented) return;
        if (e.button !== 0) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        const anchor = e.target.closest('a[href]');
        const url = softNavTargetFromAnchor(anchor);
        if (!url) return;
        e.preventDefault();
        e.stopPropagation();
        softNavigate(url);
    }, true);

    window.addEventListener('popstate', () => {
        if (state.status === 'idle') return;
        softNavigate(window.location.href, { push: false });
    });

    // Public API
    window.HoshiCall = {
        startVoice(conversationId, remoteUser) {
            return startCall({ conversationId, mode: 'voice', remoteUser });
        },
        startVideo(conversationId, remoteUser) {
            return startCall({ conversationId, mode: 'video', remoteUser });
        },
        handleSignal,
        bindChatSocket,
        ensureOverlay,
        bootPopup,
        isBusy() {
            if (state.status !== 'idle') return true;
            try {
                return !!(callPopupRef && !callPopupRef.closed);
            } catch (_) {
                return false;
            }
        },
        minimize() {
            setMinimized(true);
        },
        expand() {
            setMinimized(false);
        },
        isMinimized() {
            return !!state.minimized;
        },
        softNavigate(url) {
            return softNavigate(url);
        },
        focusCallWindow() {
            if (callPopupRef && !callPopupRef.closed) {
                try { callPopupRef.focus(); } catch (_) { /* ignore */ }
                return true;
            }
            return false;
        },
    };

    if (callBus) {
        callBus.addEventListener('message', (event) => {
            const data = event.data || {};
            if (IS_CALL_POPUP) return;
            if (data.type === 'call_popup_ready') {
                if (state.status === 'handoff'
                    && (!data.call_id || data.call_id === state.callId)) {
                    finishHandoffToIdle();
                }
                return;
            }
            if (data.type === 'call_ended') {
                callPopupRef = null;
                if (state.status === 'handoff') {
                    finishHandoffToIdle();
                }
            }
        });
    }

    window.addEventListener('beforeunload', (e) => {
        if (state.status === 'idle') return;
        // Tab chính đang handoff / cuộc gọi nằm ở popup → không chặn F5
        if (!IS_CALL_POPUP && (state.status === 'handoff'
            || state.status === 'outgoing' || state.status === 'active' || state.status === 'connecting')) {
            if (callPopupRef && !callPopupRef.closed) return;
        }
        e.preventDefault();
        e.returnValue = 'Bạn đang trong cuộc gọi. Rời trang sẽ cắt cuộc gọi.';
        return e.returnValue;
    });

    window.addEventListener('pagehide', () => {
        if (IS_CALL_POPUP) return; // popup đã gắn listener riêng trong bootPopup
        leaveCallOnPageExit();
    });

    document.addEventListener('DOMContentLoaded', () => {
        if (!IS_CALL_POPUP) ensureOverlay();
    });
})(window);
