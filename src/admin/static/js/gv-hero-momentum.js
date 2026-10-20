(() => {
    'use strict';

    const hero =
        document.querySelector('section.relative.min-h-screen.overflow-hidden') ||
        document.querySelector('body section:first-of-type');

    if (!hero) return;

    let startY = 0;
    let lastY = 0;
    let lastTime = 0;
    let velocity = 0;
    let tracking = false;
    let inertiaFrame = null;

    const stopInertia = () => {
        if (inertiaFrame) {
            cancelAnimationFrame(inertiaFrame);
            inertiaFrame = null;
        }
    };

    const onTouchStart = (event) => {
        if (event.touches.length !== 1) return;

        stopInertia();

        const touch = event.touches[0];

        startY = touch.clientY;
        lastY = touch.clientY;
        lastTime = performance.now();
        velocity = 0;
        tracking = true;
    };

    const onTouchMove = (event) => {
        if (!tracking || event.touches.length !== 1) return;

        const touch = event.touches[0];
        const now = performance.now();

        const dy = lastY - touch.clientY;
        const dt = Math.max(8, now - lastTime);

        // مثبت = حرکت رو به بالا
        const instantVelocity = dy / dt;

        // نرم کردن سرعت برای جلوگیری از پرش
        velocity = velocity * 0.65 + instantVelocity * 0.35;

        lastY = touch.clientY;
        lastTime = now;
    };

    const onTouchEnd = () => {
        if (!tracking) return;

        tracking = false;

        const distance = startY - lastY;

        // فقط Swipe رو به بالا
        if (distance < 25 || velocity < 0.18) {
            velocity = 0;
            return;
        }

        // سقف سرعت برای اینکه حرکت بیش از حد نشود
        let v = Math.min(0.70, velocity);

        let previousTime = performance.now();
        const startedAt = previousTime;

        const animate = (now) => {
            const dt = Math.min(32, now - previousTime);
            previousTime = now;

            // ادامه حرکت خیلی کوتاه و نرم
            window.scrollBy(0, v * dt);

            // اصطکاک
            v *= Math.pow(0.88, dt / 16);

            const elapsed = now - startedAt;

            if (v > 0.035 && elapsed < 320) {
                inertiaFrame = requestAnimationFrame(animate);
            } else {
                inertiaFrame = null;
            }
        };

        inertiaFrame = requestAnimationFrame(animate);
    };

    hero.addEventListener('touchstart', onTouchStart, { passive: true });
    hero.addEventListener('touchmove', onTouchMove, { passive: true });
    hero.addEventListener('touchend', onTouchEnd, { passive: true });
    hero.addEventListener('touchcancel', onTouchEnd, { passive: true });

    // برای جلوگیری از اجرای دوباره در صورت partial navigation
    window.__gvHeroMomentumCleanup = () => {
        stopInertia();

        hero.removeEventListener('touchstart', onTouchStart);
        hero.removeEventListener('touchmove', onTouchMove);
        hero.removeEventListener('touchend', onTouchEnd);
        hero.removeEventListener('touchcancel', onTouchEnd);
    };
})();
