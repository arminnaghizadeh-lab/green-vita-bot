(() => {
  function setup() {
    const body = document.body;
    const header = document.querySelector('header.site-header');
    if (!body || !header) return;

    const basePadding = parseFloat(getComputedStyle(body).paddingTop) || 0;
    let appliedOffset = 0;

    function firstFlowContent() {
      let el = header.nextElementSibling;

      while (el) {
        const tag = el.tagName;
        if (['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'TEMPLATE'].includes(tag)) {
          el = el.nextElementSibling;
          continue;
        }

        const cs = getComputedStyle(el);
        if (
          cs.display === 'none' ||
          cs.visibility === 'hidden' ||
          cs.position === 'fixed' ||
          cs.position === 'absolute' ||
          el.matches('footer, .site-footer, .gv-footer')
        ) {
          el = el.nextElementSibling;
          continue;
        }

        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) return el;
        el = el.nextElementSibling;
      }

      return null;
    }

    function correctOffset() {
      // هنگام بازبودن منوی موبایل، محتوای صفحه جابه‌جا نشود.
      if (header.classList.contains('gv-mobile-open')) return;

      const content = firstFlowContent();
      if (!content) return;

      const headerBottom = header.getBoundingClientRect().bottom;
      const currentTop = content.getBoundingClientRect().top;
      const naturalTop = currentTop - appliedOffset;
      const needed = Math.max(0, Math.ceil(headerBottom + 4 - naturalTop));

      if (needed === appliedOffset) return;

      body.style.setProperty(
        'padding-top',
        `${basePadding + needed}px`,
        'important'
      );

      appliedOffset = needed;
    }

    const update = () => requestAnimationFrame(correctOffset);

    if (document.fonts?.ready) {
      document.fonts.ready.then(update);
    }

    update();
    window.addEventListener('load', update, { once: true });
    window.addEventListener('resize', update);
    window.addEventListener('orientationchange', update);

    if ('ResizeObserver' in window) {
      new ResizeObserver(update).observe(header);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup, { once: true });
  } else {
    setup();
  }
})();
