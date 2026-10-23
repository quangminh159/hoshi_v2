/**
 * Moora mobile adapt — tự chỉnh theo từng máy (notch, thanh Safari, xoay màn hình).
 * Ghi CSS vars lên <html>: --app-height, --app-vh, --safe-*, data-touch / data-standalone.
 */
(function () {
    'use strict';

    var root = document.documentElement;
    var raf = 0;

    function num(v, fallback) {
        var n = parseFloat(v);
        return Number.isFinite(n) ? n : fallback;
    }

    function readSafeInsets() {
        var probe = document.createElement('div');
        probe.style.cssText =
            'position:fixed;inset:0;padding:' +
            'env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) ' +
            'env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px);' +
            'pointer-events:none;visibility:hidden;z-index:-1';
        document.body.appendChild(probe);
        var cs = getComputedStyle(probe);
        var insets = {
            top: num(cs.paddingTop, 0),
            right: num(cs.paddingRight, 0),
            bottom: num(cs.paddingBottom, 0),
            left: num(cs.paddingLeft, 0),
        };
        probe.remove();
        return insets;
    }

    function viewportHeight() {
        if (window.visualViewport && window.visualViewport.height) {
            return Math.round(window.visualViewport.height);
        }
        return Math.round(window.innerHeight || root.clientHeight || 0);
    }

    function viewportWidth() {
        if (window.visualViewport && window.visualViewport.width) {
            return Math.round(window.visualViewport.width);
        }
        return Math.round(window.innerWidth || root.clientWidth || 0);
    }

    function isTouchDevice() {
        try {
            if (window.matchMedia('(hover: none) and (pointer: coarse)').matches) return true;
        } catch (_) {}
        return 'ontouchstart' in window || (navigator.maxTouchPoints || 0) > 0;
    }

    function isStandalone() {
        try {
            if (window.matchMedia('(display-mode: standalone)').matches) return true;
        } catch (_) {}
        return !!navigator.standalone;
    }

    function apply() {
        var h = Math.max(1, viewportHeight());
        var w = Math.max(1, viewportWidth());
        root.style.setProperty('--app-height', h + 'px');
        root.style.setProperty('--app-vh', h / 100 + 'px');
        root.style.setProperty('--app-width', w + 'px');

        var safe = document.body ? readSafeInsets() : { top: 0, right: 0, bottom: 0, left: 0 };
        root.style.setProperty('--safe-top', safe.top + 'px');
        root.style.setProperty('--safe-right', safe.right + 'px');
        root.style.setProperty('--safe-bottom', safe.bottom + 'px');
        root.style.setProperty('--safe-left', safe.left + 'px');

        var topbar = 52 + safe.top;
        var bottomNav = 60 + safe.bottom;
        root.style.setProperty('--mobile-topbar-h', topbar + 'px');
        root.style.setProperty('--mobile-nav-h', bottomNav + 'px');
        root.style.setProperty('--mobile-main-pad-top', topbar + 'px');
        root.style.setProperty('--mobile-main-pad-bottom', bottomNav + 12 + 'px');

        root.classList.toggle('is-touch', isTouchDevice());
        root.classList.toggle('is-standalone', isStandalone());
        root.dataset.orientation = w >= h ? 'landscape' : 'portrait';

        window.dispatchEvent(
            new CustomEvent('hoshi:viewport', {
                detail: { height: h, width: w, safe: safe },
            })
        );
    }

    function schedule() {
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(function () {
            raf = 0;
            apply();
        });
    }

    apply();

    window.addEventListener('resize', schedule, { passive: true });
    window.addEventListener('orientationchange', function () {
        setTimeout(schedule, 120);
        setTimeout(schedule, 400);
    }, { passive: true });

    if (window.visualViewport) {
        visualViewport.addEventListener('resize', schedule, { passive: true });
        visualViewport.addEventListener('scroll', schedule, { passive: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', schedule);
    } else {
        schedule();
    }

    window.HoshiMobileAdapt = { refresh: apply };
})();
