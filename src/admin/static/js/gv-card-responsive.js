(() => {
  const init = () => {
    const cards = [
      ...document.querySelectorAll(
        '.gv-home-services .services > .service'
      )
    ];

    if (cards.length < 4) {
      return;
    }

    const master = cards[0];

    const applyMasterHeight = () => {
      const masterHeight = master.getBoundingClientRect().height;

      cards.slice(1).forEach(card => {
        card.style.setProperty(
          'height',
          `${masterHeight}px`,
          'important'
        );

        card.style.setProperty(
          'min-height',
          `${masterHeight}px`,
          'important'
        );
      });
    };

    let timer = null;

    const onResize = () => {
      clearTimeout(timer);

      timer = setTimeout(() => {
        cards.slice(1).forEach(card => {
          card.style.removeProperty('height');
          card.style.removeProperty('min-height');
        });

        requestAnimationFrame(applyMasterHeight);
      }, 80);
    };

    window.addEventListener('resize', onResize, {
      passive: true
    });

    const observer = new ResizeObserver(() => {
      requestAnimationFrame(applyMasterHeight);
    });

    observer.observe(master);

    applyMasterHeight();

    window.__gvCardResponsiveCleanup = () => {
      clearTimeout(timer);
      window.removeEventListener('resize', onResize);
      observer.disconnect();

      cards.slice(1).forEach(card => {
        card.style.removeProperty('height');
        card.style.removeProperty('min-height');
      });
    };

    console.log('✅ GV CARD HEIGHT MASTER ACTIVE');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
