/**
 * Hoshi theme: light / dark / system
 * Persists to localStorage key `hoshi-theme`
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'hoshi-theme';
    const MODES = ['light', 'dark', 'system'];

    function getStoredMode() {
        const value = localStorage.getItem(STORAGE_KEY);
        return MODES.includes(value) ? value : 'system';
    }

    function systemPrefersDark() {
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function resolveTheme(mode) {
        if (mode === 'dark') return 'dark';
        if (mode === 'light') return 'light';
        return systemPrefersDark() ? 'dark' : 'light';
    }

    function applyTheme(mode) {
        const resolved = resolveTheme(mode);
        document.documentElement.setAttribute('data-bs-theme', resolved);
        document.documentElement.setAttribute('data-theme-mode', mode);
        document.documentElement.style.colorScheme = resolved;

        document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
            const label = resolved === 'dark' ? 'Chuyển sang sáng' : 'Chuyển sang tối';
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);
        });

        document.querySelectorAll('[data-theme-option]').forEach((el) => {
            el.classList.toggle('is-active', el.getAttribute('data-theme-option') === mode);
        });

        window.dispatchEvent(new CustomEvent('hoshi:themechange', {
            detail: { mode, theme: resolved },
        }));
    }

    function setMode(mode) {
        const next = MODES.includes(mode) ? mode : 'system';
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
    }

    function cycleMode() {
        const current = getStoredMode();
        // Nút nhanh trên navbar: đảo light <-> dark (giữ system nếu đang system thì nhảy sang ngược hệ thống)
        if (current === 'system') {
            setMode(systemPrefersDark() ? 'light' : 'dark');
            return;
        }
        setMode(current === 'dark' ? 'light' : 'dark');
    }

    // Expose ASAP for inline boot + settings
    window.HoshiTheme = {
        getMode: getStoredMode,
        getResolved: () => resolveTheme(getStoredMode()),
        setMode,
        cycleMode,
        applyTheme,
    };

    function bindUi() {
        document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                cycleMode();
            });
        });

        document.querySelectorAll('[data-theme-option]').forEach((el) => {
            if (el.dataset.bound === '1') return;
            el.dataset.bound = '1';
            el.addEventListener('click', (e) => {
                e.preventDefault();
                setMode(el.getAttribute('data-theme-option'));
            });
        });

        applyTheme(getStoredMode());
    }

    if (window.matchMedia) {
        const mq = window.matchMedia('(prefers-color-scheme: dark)');
        const onChange = () => {
            if (getStoredMode() === 'system') applyTheme('system');
        };
        if (mq.addEventListener) mq.addEventListener('change', onChange);
        else if (mq.addListener) mq.addListener(onChange);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindUi);
    } else {
        bindUi();
    }
})();
