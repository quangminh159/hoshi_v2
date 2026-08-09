/**
 * Hoshi Like Effects
 * -------------------
 * File riêng cho hiệu ứng khi thả tim. Mặc định: cờ Việt Nam bay lên.
 *
 * Thêm hiệu ứng mới:
 *   HoshiLikeEffects.register('ten_hieu_ung', function (anchor, ctx) {
 *     // anchor = nút like; ctx.spawn(html, opts) tạo particle
 *   });
 *   HoshiLikeEffects.setActive('ten_hieu_ung');
 *
 * Tắt hiệu ứng: HoshiLikeEffects.setActive('none')
 * Xem danh sách: HoshiLikeEffects.list()
 *
 * Ngày lễ VN có sẵn:
 *   hoa | hoa_dao | hoa_mai | hoa_sen | tet | trung_thu |
 *   quoc_khanh | gio_to | 8_3 | 20_10 | 20_11 | 1_6 | noel | valentine | 14_2
 *   + vietnam_flag | hearts | confetti
 *
 * Vui / độc lạ:
 *   meme | cat | dog | frog | food | bubble_tea | money |
 *   rocket | rainbow | disco | alien | ghost | fire | ice |
 *   lol | random
 */
(function (window, document) {
    'use strict';

    const STORAGE_KEY = 'hoshi_like_effect';
    const DEFAULT_EFFECT = 'valentine';

    const registry = Object.create(null);
    let activeName = DEFAULT_EFFECT;

    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) activeName = saved;
    } catch (_) { /* ignore */ }

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function ensureLayer() {
        let layer = document.getElementById('hoshi-like-fx-layer');
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'hoshi-like-fx-layer';
            layer.className = 'hoshi-like-fx-layer';
            layer.setAttribute('aria-hidden', 'true');
            document.body.appendChild(layer);
        }
        return layer;
    }

    /**
     * @param {HTMLElement} anchor
     * @param {string} html
     * @param {{
     *   className?: string,
     *   duration?: number,
     *   dx?: number,
     *   dy?: number,
     *   scale?: number,
     *   rotate?: number,
     *   delay?: number,
     * }} [opts]
     */
    function spawn(anchor, html, opts) {
        opts = opts || {};
        const layer = ensureLayer();
        const rect = anchor.getBoundingClientRect();
        const el = document.createElement('span');
        el.className = 'hoshi-like-fx-particle' + (opts.className ? ' ' + opts.className : '');
        el.innerHTML = html;

        const originX = rect.left + rect.width / 2 + (opts.originOffsetX || 0);
        const originY = rect.top + rect.height / 2 + (opts.originOffsetY || 0);
        el.style.left = originX + 'px';
        el.style.top = originY + 'px';

        const duration = opts.duration != null ? opts.duration : 1100;
        const dx = opts.dx != null ? opts.dx : rand(-40, 40);
        const dy = opts.dy != null ? opts.dy : rand(-120, -70);
        const scale = opts.scale != null ? opts.scale : rand(0.85, 1.25);
        const rotate = opts.rotate != null ? opts.rotate : rand(-25, 25);
        const delay = opts.delay || 0;

        el.style.setProperty('--fx-dx', dx + 'px');
        el.style.setProperty('--fx-dy', dy + 'px');
        el.style.setProperty('--fx-scale', String(scale));
        el.style.setProperty('--fx-rotate', rotate + 'deg');
        el.style.setProperty('--fx-duration', duration + 'ms');
        el.style.setProperty('--fx-delay', delay + 'ms');

        layer.appendChild(el);
        window.setTimeout(() => el.remove(), duration + delay + 80);
        return el;
    }

    function makeContext(anchor) {
        return {
            anchor: anchor,
            spawn: function (html, opts) {
                return spawn(anchor, html, opts);
            },
            rand: rand,
            pulseButton: function () {
                anchor.classList.remove('hoshi-like-fx-pulse');
                // restart animation
                void anchor.offsetWidth;
                anchor.classList.add('hoshi-like-fx-pulse');
                window.setTimeout(() => anchor.classList.remove('hoshi-like-fx-pulse'), 450);
            },
        };
    }

    function play(anchor, effectName) {
        if (!anchor) return;
        const name = effectName || activeName;
        if (!name || name === 'none') return;
        const fn = registry[name];
        if (typeof fn !== 'function') return;
        try {
            fn(anchor, makeContext(anchor));
        } catch (err) {
            console.warn('[HoshiLikeEffects]', err);
        }
    }

    function register(name, fn) {
        if (!name || typeof fn !== 'function') return;
        registry[name] = fn;
    }

    function setActive(name) {
        if (name !== 'none' && !registry[name]) {
            console.warn('[HoshiLikeEffects] effect không tồn tại:', name);
            return;
        }
        activeName = name;
        try {
            localStorage.setItem(STORAGE_KEY, name);
        } catch (_) { /* ignore */ }
    }

    function getActive() {
        return activeName;
    }

    function list() {
        return Object.keys(registry).concat(['none']);
    }

    /* ---------- Built-in effects ---------- */

    /** Cờ Việt Nam bay lên từ nút tim */
    register('vietnam_flag', function (anchor, ctx) {
        ctx.pulseButton();
        const count = 7 + Math.floor(rand(0, 4));
        for (let i = 0; i < count; i++) {
            ctx.spawn(
                '<span class="hoshi-vn-flag" title="Việt Nam">' +
                    '<span class="hoshi-vn-flag__star">★</span>' +
                '</span>',
                {
                    className: 'hoshi-like-fx--flag',
                    delay: i * 45,
                    duration: rand(900, 1400),
                    dx: rand(-55, 55),
                    dy: rand(-150, -85),
                    scale: rand(0.75, 1.2),
                    rotate: rand(-30, 30),
                }
            );
        }
        // vài ngôi sao vàng nhỏ kèm theo
        for (let i = 0; i < 4; i++) {
            ctx.spawn('<span class="hoshi-vn-star">★</span>', {
                className: 'hoshi-like-fx--star',
                delay: 80 + i * 60,
                duration: rand(700, 1100),
                dx: rand(-70, 70),
                dy: rand(-130, -60),
                scale: rand(0.6, 1.1),
                rotate: rand(-40, 40),
            });
        }
    });

    /** Tim đỏ bay lên (ví dụ hiệu ứng khác) */
    register('hearts', function (anchor, ctx) {
        ctx.pulseButton();
        const emojis = ['❤️', '💕', '💗', '💖'];
        const count = 8;
        for (let i = 0; i < count; i++) {
            ctx.spawn(emojis[i % emojis.length], {
                className: 'hoshi-like-fx--emoji',
                delay: i * 40,
                duration: rand(800, 1300),
                dx: rand(-50, 50),
                dy: rand(-140, -80),
                scale: rand(0.8, 1.35),
                rotate: rand(-20, 20),
            });
        }
    });

    /** Pháo giấy nhẹ */
    register('confetti', function (anchor, ctx) {
        ctx.pulseButton();
        const colors = ['#da251d', '#ffff00', '#405de6', '#ed4956', '#22c55e', '#f59e0b'];
        for (let i = 0; i < 14; i++) {
            const color = colors[i % colors.length];
            ctx.spawn(
                `<span class="hoshi-confetti" style="background:${color}"></span>`,
                {
                    className: 'hoshi-like-fx--confetti',
                    delay: i * 25,
                    duration: rand(700, 1200),
                    dx: rand(-80, 80),
                    dy: rand(-160, -70),
                    scale: rand(0.7, 1.3),
                    rotate: rand(-180, 180),
                }
            );
        }
    });

    /** Burst emoji dùng chung cho ngày lễ */
    function burstEmojis(ctx, emojis, opts) {
        opts = opts || {};
        ctx.pulseButton();
        const count = opts.count != null ? opts.count : 10;
        const className = opts.className || 'hoshi-like-fx--emoji';
        for (let i = 0; i < count; i++) {
            const item = emojis[i % emojis.length];
            ctx.spawn(item, {
                className: className,
                delay: (opts.stagger != null ? opts.stagger : 40) * i,
                duration: rand(opts.minDuration || 850, opts.maxDuration || 1400),
                dx: rand(opts.minDx != null ? opts.minDx : -55, opts.maxDx != null ? opts.maxDx : 55),
                dy: rand(opts.minDy != null ? opts.minDy : -155, opts.maxDy != null ? opts.maxDy : -80),
                scale: rand(opts.minScale || 0.8, opts.maxScale || 1.4),
                rotate: rand(opts.minRotate != null ? opts.minRotate : -30, opts.maxRotate != null ? opts.maxRotate : 30),
            });
        }
    }

    /** Hoa tổng hợp (đào, mai, sen, hướng dương…) */
    register('hoa', function (anchor, ctx) {
        burstEmojis(ctx, ['🌸', '🌺', '🌼', '🌻', '🌷', '🌹', '💮', '🏵️'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--flower',
        });
    });

    /** Hoa đào — mùa xuân / Tết Bắc */
    register('hoa_dao', function (anchor, ctx) {
        burstEmojis(ctx, ['🌸', '🌺', '🩷', '💮'], {
            count: 11,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--peach',
            minScale: 0.9,
            maxScale: 1.5,
        });
    });

    /** Hoa mai vàng — Tết Nam */
    register('hoa_mai', function (anchor, ctx) {
        burstEmojis(ctx, ['🌼', '🌻', '⭐', '💛', '✨'], {
            count: 11,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--mai',
        });
    });

    /** Hoa sen — ngày Phật Đản / thanh khiết */
    register('hoa_sen', function (anchor, ctx) {
        burstEmojis(ctx, ['🪷', '🌸', '💜', '✨'], {
            count: 10,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--lotus',
            minDy: -140,
            maxDy: -70,
        });
    });

    /** Tết Nguyên Đán — mai, đào, lì xì, pháo hoa */
    register('tet', function (anchor, ctx) {
        burstEmojis(ctx, ['🧧', '🌸', '🌼', '🎆', '✨', '🍊', '🧨', '💛'], {
            count: 14,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--tet',
            stagger: 35,
            minDuration: 900,
            maxDuration: 1500,
        });
    });

    /** Trung thu — đèn lồng, trăng, bánh */
    register('trung_thu', function (anchor, ctx) {
        burstEmojis(ctx, ['🏮', '🌝', '🥮', '⭐', '✨', '🐇', '🌕'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--midautumn',
        });
    });

    /** Quốc khánh 2/9 — cờ + pháo hoa */
    register('quoc_khanh', function (anchor, ctx) {
        ctx.pulseButton();
        for (let i = 0; i < 5; i++) {
            ctx.spawn(
                '<span class="hoshi-vn-flag"><span class="hoshi-vn-flag__star">★</span></span>',
                {
                    className: 'hoshi-like-fx--flag',
                    delay: i * 50,
                    duration: rand(1000, 1450),
                    dx: rand(-50, 50),
                    dy: rand(-150, -90),
                    scale: rand(0.8, 1.2),
                    rotate: rand(-25, 25),
                }
            );
        }
        burstEmojis(ctx, ['🎆', '🎇', '⭐', '💛', '✨'], {
            count: 10,
            className: 'hoshi-like-fx--emoji',
            stagger: 45,
        });
    });

    /** Giỗ Tổ Hùng Vương — hương + sen */
    register('gio_to', function (anchor, ctx) {
        burstEmojis(ctx, ['🪷', '🕯️', '🙏', '🌾', '✨'], {
            count: 10,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--gioto',
        });
    });

    /** 8/3 — Ngày Quốc tế Phụ nữ */
    register('8_3', function (anchor, ctx) {
        burstEmojis(ctx, ['🌷', '🌹', '💐', '💖', '🌸', '🎀'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--flower',
        });
    });

    /** 20/10 — Ngày Phụ nữ Việt Nam */
    register('20_10', function (anchor, ctx) {
        burstEmojis(ctx, ['💐', '🌹', '🌸', '💗', '🎀', '✨'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--flower',
        });
    });

    /** 20/11 — Ngày Nhà giáo Việt Nam */
    register('20_11', function (anchor, ctx) {
        burstEmojis(ctx, ['🌹', '📚', '✏️', '💐', '🌸', '⭐'], {
            count: 11,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** 1/6 — Quốc tế Thiếu nhi */
    register('1_6', function (anchor, ctx) {
        burstEmojis(ctx, ['🎈', '🎁', '🍭', '🌟', '🧸', '🎉'], {
            count: 12,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** Noel kiểu Việt — nhẹ nhàng */
    register('noel', function (anchor, ctx) {
        burstEmojis(ctx, ['🎄', '⭐', '🎁', '❄️', '🔔', '✨'], {
            count: 11,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** 14/2 — Valentine / Lễ tình nhân */
    register('valentine', function (anchor, ctx) {
        burstEmojis(ctx, ['❤️', '💕', '💖', '💗', '💘', '💝', '🌹', '🍫', '💌', '😘'], {
            count: 14,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--valentine',
            stagger: 35,
            minScale: 0.9,
            maxScale: 1.5,
            minDy: -160,
            maxDy: -85,
        });
    });
    register('14_2', function (anchor, ctx) {
        registry.valentine(anchor, ctx);
    });

    /* ---------- Hiệu ứng vui / độc lạ ---------- */

    /** Meme reaction bay lên */
    register('meme', function (anchor, ctx) {
        burstEmojis(ctx, ['😂', '💀', '😭', '🔥', '🤡', '👀', '🫡', '💅'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
            stagger: 35,
        });
    });

    /** Mèo spam */
    register('cat', function (anchor, ctx) {
        burstEmojis(ctx, ['🐱', '😺', '😸', '😹', '😻', '🐈', '🐾'], {
            count: 11,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
        });
    });

    /** Cún cưng */
    register('dog', function (anchor, ctx) {
        burstEmojis(ctx, ['🐶', '🐕', '🦮', '🦴', '🐾', '🌭'], {
            count: 11,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
        });
    });

    /** Ếch / pepe vibe */
    register('frog', function (anchor, ctx) {
        burstEmojis(ctx, ['🐸', '🍃', '💧', '🟢', '✨'], {
            count: 10,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
        });
    });

    /** Đồ ăn thèm thuồng */
    register('food', function (anchor, ctx) {
        burstEmojis(ctx, ['🍜', '🍲', '🧋', '🍙', '🥟', '🍤', '🥖', '🍦', '🍕'], {
            count: 12,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** Trà sữa */
    register('bubble_tea', function (anchor, ctx) {
        burstEmojis(ctx, ['🧋', '🧋', '🧋', '💕', '✨', '🥤'], {
            count: 10,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
        });
    });

    /** Tiền bay — giàu ơi là giàu */
    register('money', function (anchor, ctx) {
        burstEmojis(ctx, ['💰', '💵', '💸', '🤑', '💎', '✨'], {
            count: 13,
            className: 'hoshi-like-fx--emoji',
            minDx: -70,
            maxDx: 70,
            minDy: -170,
            maxDy: -90,
        });
    });

    /** Rocket launch */
    register('rocket', function (anchor, ctx) {
        ctx.pulseButton();
        ctx.spawn('🚀', {
            className: 'hoshi-like-fx--emoji hoshi-like-fx--rocket',
            duration: 1400,
            dx: rand(-10, 10),
            dy: -220,
            scale: 1.6,
            rotate: -20,
        });
        burstEmojis(ctx, ['💨', '⭐', '✨', '🔥'], {
            count: 8,
            stagger: 50,
            minDy: -160,
            maxDy: -100,
        });
    });

    /** Cầu vồng chữ */
    register('rainbow', function (anchor, ctx) {
        ctx.pulseButton();
        const letters = [
            { t: 'L', c: '#ff0000' },
            { t: 'O', c: '#ff7f00' },
            { t: 'V', c: '#ffff00' },
            { t: 'E', c: '#00ff00' },
            { t: '❤', c: '#00bfff' },
            { t: 'U', c: '#8b00ff' },
        ];
        letters.forEach((item, i) => {
            ctx.spawn(
                `<span class="hoshi-fx-letter" style="color:${item.c}">${item.t}</span>`,
                {
                    className: 'hoshi-like-fx--letter',
                    delay: i * 70,
                    duration: 1200,
                    dx: -50 + i * 20,
                    dy: rand(-140, -90),
                    scale: 1.2,
                    rotate: rand(-15, 15),
                }
            );
        });
    });

    /** Disco party */
    register('disco', function (anchor, ctx) {
        burstEmojis(ctx, ['🪩', '🕺', '💃', '🎶', '✨', '💜', '💖', '🎉'], {
            count: 14,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--disco',
            stagger: 30,
            minRotate: -60,
            maxRotate: 60,
        });
    });

    /** Alien invasion */
    register('alien', function (anchor, ctx) {
        burstEmojis(ctx, ['👽', '🛸', '🌌', '⭐', '👾', '🟢'], {
            count: 11,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** Ma quái dễ thương */
    register('ghost', function (anchor, ctx) {
        burstEmojis(ctx, ['👻', '🎃', '🦇', '💀', '👀', '✨'], {
            count: 10,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** Lửa cháy máy */
    register('fire', function (anchor, ctx) {
        burstEmojis(ctx, ['🔥', '🔥', '💥', '⚡', '✨', '❤️‍🔥'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--fire',
            minDy: -170,
            maxDy: -95,
        });
    });

    /** Băng giá */
    register('ice', function (anchor, ctx) {
        burstEmojis(ctx, ['❄️', '🧊', '🌨️', '💎', '✨', '🥶'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--ice',
        });
    });

    /** LOL text + emoji */
    register('lol', function (anchor, ctx) {
        ctx.pulseButton();
        ['Haha', 'LOL', 'hehe', '🙂', '😂'].forEach((t, i) => {
            ctx.spawn(
                `<span class="hoshi-fx-bubble">${t}</span>`,
                {
                    className: 'hoshi-like-fx--bubble',
                    delay: i * 80,
                    duration: rand(900, 1300),
                    dx: rand(-60, 60),
                    dy: rand(-150, -85),
                    scale: rand(0.9, 1.3),
                    rotate: rand(-12, 12),
                }
            );
        });
    });

    /** Sao băng */
    register('stars', function (anchor, ctx) {
        burstEmojis(ctx, ['⭐', '🌟', '✨', '💫', '☄️', '🌙'], {
            count: 12,
            className: 'hoshi-like-fx--emoji',
            minDx: -80,
            maxDx: 80,
            minDy: -180,
            maxDy: -100,
        });
    });

    /** Pokémon-ish cute creatures */
    register('cute', function (anchor, ctx) {
        burstEmojis(ctx, ['🐻', '🐼', '🐨', '🦊', '🐰', '🐥', '🦄', '🍭'], {
            count: 12,
            className: 'hoshi-like-fx--emoji hoshi-like-fx--big',
        });
    });

    /** Phở / đồ Việt vui */
    register('pho', function (anchor, ctx) {
        burstEmojis(ctx, ['🍜', '🍲', '🥖', '☕', '🌿', '🌶️', '😋'], {
            count: 11,
            className: 'hoshi-like-fx--emoji',
        });
    });

    /** Random — mỗi lần like một kiểu khác */
    const RANDOM_POOL = [
        'vietnam_flag', 'hoa', 'tet', 'meme', 'cat', 'dog', 'frog',
        'food', 'bubble_tea', 'money', 'rocket', 'rainbow', 'disco',
        'alien', 'ghost', 'fire', 'ice', 'lol', 'stars', 'cute', 'pho', 'hearts', 'valentine',
    ];
    register('random', function (anchor, ctx) {
        const name = RANDOM_POOL[Math.floor(Math.random() * RANDOM_POOL.length)];
        const fn = registry[name];
        if (typeof fn === 'function') fn(anchor, ctx);
    });

    function isCurrentlyLiked(btn) {
        if (btn.classList.contains('liked')) return true;
        const icon = btn.querySelector('i');
        return !!(icon && icon.classList.contains('fas') && icon.classList.contains('fa-heart'));
    }

    // Capture: chạy trước handler like → nếu chưa like thì sắp thả tim → phát hiệu ứng
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.like-button, .comment-like-button');
        if (!btn) return;
        if (isCurrentlyLiked(btn)) return; // đang unlike → không hiệu ứng
        play(btn);
    }, true);

    window.HoshiLikeEffects = {
        register: register,
        setActive: setActive,
        getActive: getActive,
        list: list,
        play: play,
        DEFAULT: DEFAULT_EFFECT,
    };
})(window, document);
