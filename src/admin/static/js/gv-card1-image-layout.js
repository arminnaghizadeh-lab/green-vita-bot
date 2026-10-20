(() => {
  const init = () => {
    const card1 = document.querySelector(
      '.gv-home-services .services > .service:first-child'
    );

    const card2 = document.querySelector(
      '.gv-home-services .services > .service:nth-child(2)'
    );

    const box1 = card1?.querySelector('.service-image');
    const box2 = card2?.querySelector('.service-image');

    if (!card1 || !card2 || !box1 || !box2) {
      return;
    }

    const apply = () => {
      const width2 = box2.getBoundingClientRect().width;

      /* عرض دقیقاً مثل کارت ۲ */
      box1.style.setProperty(
        'width',
        `${width2}px`,
        'important'
      );

      box1.style.setProperty(
        'min-width',
        `${width2}px`,
        'important'
      );

      box1.style.setProperty(
        'max-width',
        `${width2}px`,
        'important'
      );

      /* حذف هر جابه‌جایی قبلی */
      box1.style.setProperty(
        'position',
        'static',
        'important'
      );

      box1.style.setProperty(
        'left',
        'auto',
        'important'
      );

      box1.style.setProperty(
        'right',
        'auto',
        'important'
      );

      box1.style.setProperty(
        'margin-left',
        'auto',
        'important'
      );

      box1.style.setProperty(
        'margin-right',
        'auto',
        'important'
      );

      box1.style.setProperty(
        'transform',
        'none',
        'important'
      );

      /* بعد از layout، اختلاف مرکز واقعی را محاسبه کن */
      requestAnimationFrame(() => {
        const cr = card1.getBoundingClientRect();
        const ir = box1.getBoundingClientRect();

        const cardCenter =
          cr.left + cr.width / 2;

        const imageCenter =
          ir.left + ir.width / 2;

        const offset =
          imageCenter - cardCenter;

        /* اصلاح دقیق مرکز */
        box1.style.setProperty(
          'transform',
          `translateX(${-offset}px)`,
          'important'
        );
      });
    };

    let timer = null;

    const onResize = () => {
      clearTimeout(timer);

      timer = setTimeout(() => {
        requestAnimationFrame(apply);
      }, 80);
    };

    window.addEventListener(
      'resize',
      onResize,
      { passive: true }
    );

    const observer = new ResizeObserver(() => {
      requestAnimationFrame(apply);
    });

    observer.observe(card1);
    observer.observe(box2);

    apply();

    window.__gvCard1ImageLayoutStop = () => {
      clearTimeout(timer);

      window.removeEventListener(
        'resize',
        onResize
      );

      observer.disconnect();
    };

    console.log(
      '✅ GV CARD 1 IMAGE LAYOUT ACTIVE'
    );
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
