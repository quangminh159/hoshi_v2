/**
 * Gọi thoại/video 1-1 (WebRTC P2P) — signaling qua WS chat / inbox.
 */
(function (window) {
    'use strict';

    const DEFAULT_ICE_SERVERS = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
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

    const state = {
        status: 'idle', // idle | outgoing | incoming | connecting | active
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
            <video id="hoshiCallLocalVideo" class="hoshi-call-local" autoplay playsinline muted></video>
            <div class="hoshi-call-voice-panel" id="hoshiCallVoicePanel">
              <img id="hoshiCallAvatar" class="hoshi-call-avatar" src="/static/img/default-avatar.png" alt="">
              <div class="hoshi-call-name" id="hoshiCallName">—</div>
              <div class="hoshi-call-status" id="hoshiCallStatus">Đang gọi...</div>
              <div class="hoshi-call-timer" id="hoshiCallTimer" hidden>0:00</div>
            </div>
            <div class="hoshi-call-controls" id="hoshiCallControls">
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
          </div>
        `;
        document.body.appendChild(root);

        $('hoshiCallMuteBtn')?.addEventListener('click', toggleMute);
        $('hoshiCallCamBtn')?.addEventListener('click', onCamButtonClick);
        $('hoshiCallHangupBtn')?.addEventListener('click', () => endCall({ reason: 'ended', writeSystem: true }));
        $('hoshiCallAcceptBtn')?.addEventListener('click', acceptIncoming);
        $('hoshiCallRejectBtn')?.addEventListener('click', () => rejectIncoming('reject'));

        return root;
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
            if (timerEl) timerEl.textContent = formatDuration(sec);
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
        syncVideoUiClasses();
        root.classList.toggle('is-incoming', !!incoming);
        root.classList.toggle('is-active', state.status === 'active');

        const name = state.remoteUser?.username || 'Người dùng';
        const avatar = state.remoteUser?.avatar_url || '/static/img/default-avatar.png';
        const nameEl = $('hoshiCallName');
        const avatarEl = $('hoshiCallAvatar');
        if (nameEl) nameEl.textContent = name;
        if (avatarEl) avatarEl.src = avatar;

        const accept = $('hoshiCallAcceptBtn');
        const reject = $('hoshiCallRejectBtn');
        const hangup = $('hoshiCallHangupBtn');
        const mute = $('hoshiCallMuteBtn');
        const cam = $('hoshiCallCamBtn');

        if (incoming) {
            if (accept) accept.hidden = false;
            if (reject) reject.hidden = false;
            if (hangup) hangup.hidden = true;
            if (mute) mute.hidden = true;
            if (cam) cam.hidden = true;
            setStatusText(state.callMode === 'video' ? 'Cuộc gọi video đến...' : 'Cuộc gọi thoại đến...');
        } else {
            if (accept) accept.hidden = true;
            if (reject) reject.hidden = true;
            if (hangup) hangup.hidden = false;
            if (mute) mute.hidden = false;
            if (cam) cam.hidden = false;
            updateCamButton();
        }
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
        }
        // Không gắn local preview nếu chưa tự bật cam
        const local = $('hoshiCallLocalVideo');
        if (local && !hasLocalVideoTrack()) {
            local.srcObject = null;
            local.hidden = true;
        }
        updateCamButton();
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
    }

    function hideOverlay() {
        const root = $('hoshiCallOverlay');
        if (root) root.hidden = true;
        const remote = $('hoshiCallRemoteVideo');
        const local = $('hoshiCallLocalVideo');
        if (remote) remote.srcObject = null;
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
        if (remote) {
            remote.srcObject = stream;
            remote.hidden = !state.remoteHasVideo;
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
            if (pc.connectionState === 'connected') {
                state.status = 'active';
                showOverlay({ incoming: false });
                setStatusText('Đang trong cuộc gọi');
                if (!state.startedAt) startTimer();
                const root = $('hoshiCallOverlay');
                if (root) root.classList.add('is-active');
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

    async function onIncomingInvite(payload) {
        if (!payload || Number(payload.from_user?.id) === currentUserId()) return;

        if (state.status !== 'idle') {
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

        state.ringTimer = setTimeout(() => {
            rejectIncoming('timeout');
        }, RING_TIMEOUT_MS);
    }

    async function acceptIncoming() {
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
        sendSignal('call_accept');
        await createPeer();
    }

    function rejectIncoming(reason) {
        if (state.status !== 'incoming' && state.status !== 'connecting') return;
        clearRingTimer();
        const writeSystem = reason === 'timeout';
        ensureSocket(state.conversationId).then(() => {
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
        }
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
    }

    function onRemoteModeChange(payload) {
        if (payload.call_mode === 'video') {
            state.remoteHasVideo = true;
            onRemoteVideoAvailable();
            setStatusText('Đối phương đã bật camera');
        }
    }

    function handleSignal(data) {
        if (!data || !data.signal) {
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
            && (state.status === 'incoming' || state.status === 'connecting' || state.status === 'outgoing')) {
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
                endCall({ reason: data.reason || 'ended', writeSystem: false, silentRemote: true });
                break;
            default:
                break;
        }
    }

    function bindChatSocket(socket, conversationId) {
        if (!socket) return;
        window.hoshiChatSocket = socket;
        window.hoshiChatConversationId = conversationId;
        // If currently using shared socket for active call, keep reference
        if (state.conversationId && Number(state.conversationId) === Number(conversationId)) {
            state.socket = socket;
            state.ownSocket = false;
        }
    }

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
        isBusy() {
            return state.status !== 'idle';
        },
    };

    document.addEventListener('DOMContentLoaded', () => {
        ensureOverlay();
    });
})(window);
