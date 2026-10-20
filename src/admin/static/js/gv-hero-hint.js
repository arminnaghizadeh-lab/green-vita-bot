(() => {
  const init = () => {
    const hero =
      document.querySelector(
        'section.relative.min-h-screen.overflow-hidden'
      ) ||
      document.querySelector(
        'body section:first-of-type'
      );

    if (!hero) {
      return;
    }

    if (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    setTimeout(() => {
      hero.animate(
        [
          { transform: 'translateY(0)' },

          /* Ding 1 */
          { transform: 'translateY(-20px)' },
          { transform: 'translateY(0)' },

          /* Ding 2 */
          { transform: 'translateY(-15px)' },
          { transform: 'translateY(0)' }
        ],
        {
          duration: 1500,
          easing: 'ease-in-out',
          fill: 'none'
        }
      );
    }, 1000);
  };

  if (document.readyState === 'loading') {
    document.addEventListener(
      'DOMContentLoaded',
      init,
      { once: true }
    );
  } else {
    init();
  }
})();
