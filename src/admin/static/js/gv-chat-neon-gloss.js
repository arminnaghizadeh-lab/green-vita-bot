(() => {
  const norm = s => String(s || '')
    .replace(/[\u200c\u200f\u00a0]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const styleId = 'gv-chat-neon-gloss-persistent-style';

  function isTarget(el) {
    const text = norm(
      el.innerText || el.textContent || el.getAttribute('aria-label')
    );
    const href = el.getAttribute('href') || '';
    const hay = text + ' ' + href;

    const platform = /بله|تلگرام|telegram|bale|ble\.ir|t\.me/i.test(hay);
    const conversation = /شروع\s*گفتگو|شروع\s*چت/i.test(text);
    const platformLink =
      /ble\.ir|bale\.(ai|me)|t\.me|telegram\.me/i.test(href);

    const chatbot = platform && (conversation || platformLink);

    // فقط تماس و واتساپ داخل منوی شناور تماس
    const inFloatingMenu = !!el.closest('.gv-contact-float-menu');
    const floatingPhone = inFloatingMenu && /^tel:/i.test(href);
    const floatingWhatsApp = inFloatingMenu &&
      /wa\.me|api\.whatsapp\.com|whatsapp/i.test(href);

    return chatbot || floatingPhone || floatingWhatsApp;
  }
  function apply() {
    if (!document.body) return;

    const targets = [
      ...document.querySelectorAll('a, button, [role="button"]')
    ].filter(isTarget);

    if (!targets.length) return;

    let style = document.getElementById(styleId);

    if (!style) {
      style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        @keyframes gvChatNeonPulse {
          0%, 100% {
            box-shadow:
              0 5px 16px rgba(158,216,74,.32),
              0 0 0 0 rgba(158,216,74,0),
              inset 0 1px 0 rgba(255,255,255,.75),
              inset 0 -2px 0 rgba(49,93,19,.15);
          }
          50% {
            box-shadow:
              0 8px 25px rgba(158,216,74,.52),
              0 0 0 5px rgba(158,216,74,.16),
              inset 0 1px 0 rgba(255,255,255,.9),
              inset 0 -2px 0 rgba(49,93,19,.12);
          }
        }

        [data-gv-chat-neon-persistent="1"]:hover {
          filter: brightness(1.08) !important;
          transform: translateY(-1px);
        }

        @media (prefers-reduced-motion: reduce) {
          [data-gv-chat-neon-persistent="1"] {
            animation: none !important;
          }
        }
      `;
      document.head.appendChild(style);
    }

    const reduceMotion =
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    targets.forEach(el => {
      el.setAttribute('data-gv-chat-neon-persistent', '1');

      el.style.setProperty(
        'background-image',
        'linear-gradient(180deg,rgba(255,255,255,.48),rgba(255,255,255,.12) 42%,transparent 52%),linear-gradient(115deg,#9ED84A,#B5F36B)',
        'important'
      );
      el.style.setProperty('background-color', '#9ED84A', 'important');
      el.style.setProperty('color', '#12351A', 'important');
      el.style.setProperty('-webkit-text-fill-color', '#12351A', 'important');
      el.style.setProperty('border', '1px solid rgba(255,255,255,.72)', 'important');

      el.style.removeProperty('box-shadow');

      el.style.setProperty(
        'animation',
        reduceMotion ? 'none' : 'gvChatNeonPulse 3s ease-in-out infinite',
        'important'
      );
      el.style.setProperty(
        'transition',
        'filter .25s ease, transform .25s ease',
        'important'
      );
    });
  }

  function start() {
    apply();

    if (document.body && !window.__gvChatNeonObserver) {
      window.__gvChatNeonObserver = new MutationObserver(apply);
      window.__gvChatNeonObserver.observe(document.body, {
        childList: true,
        subtree: true
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
