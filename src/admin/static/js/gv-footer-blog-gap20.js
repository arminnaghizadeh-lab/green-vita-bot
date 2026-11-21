/* GV FOOTER — EXACT 20PX GAP AFTER BLOG — PERMANENT V2 */
(() => {
  if (window.__gvFooterBlogGap20InstalledV2) return;

  function initialize() {
    if (window.__gvFooterBlogGap20InstalledV2) return;

    const blog = document.querySelector("#blog");
    const footer = document.querySelector(".gv-footer");

    if (!blog || !footer) {
      console.error("GV Footer Gap: blog/footer not found after DOM load.");
      return;
    }

    window.__gvFooterBlogGap20InstalledV2 = true;

    const TARGET_GAP = 20;
    const baseMargin = parseFloat(getComputedStyle(footer).marginTop) || 0;

    let rafId = 0;
    let resizeTimer = 0;

    function apply() {
      // Reset only our own margin before measuring.
      footer.style.setProperty(
        "margin-top",
        `${baseMargin}px`,
        "important"
      );

      // Force layout measurement.
      const blogBottom = blog.getBoundingClientRect().bottom;
      const footerTop = footer.getBoundingClientRect().top;
      const currentGap = footerTop - blogBottom;

      // Move the entire footer in normal document flow.
      let targetMargin = baseMargin + TARGET_GAP - currentGap;

      footer.style.setProperty(
        "margin-top",
        `${targetMargin}px`,
        "important"
      );

      // Verify and correct small layout rounding differences.
      const actualGap =
        footer.getBoundingClientRect().top -
        blog.getBoundingClientRect().bottom;

      if (Math.abs(actualGap - TARGET_GAP) > 0.5) {
        targetMargin += TARGET_GAP - actualGap;

        footer.style.setProperty(
          "margin-top",
          `${targetMargin}px`,
          "important"
        );
      }

      requestAnimationFrame(() => {
        const finalGap =
          footer.getBoundingClientRect().top -
          blog.getBoundingClientRect().bottom;

        if (Math.abs(finalGap - TARGET_GAP) <= 1.5) {
          console.log(
            `GV Footer Gap V2 active: ${finalGap.toFixed(1)}px`
          );
        } else {
          console.error(
            "GV Footer Gap V2 verification failed:",
            finalGap
          );
        }
      });
    }

    function schedule() {
      if (rafId) cancelAnimationFrame(rafId);

      rafId = requestAnimationFrame(() => {
        rafId = 0;
        apply();
      });
    }

    // Run after the complete page structure is available.
    schedule();
    window.addEventListener("load", schedule, { once: true });

    // Keep the gap correct after responsive layout changes.
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(schedule, 180);
    }, { passive: true });

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(schedule);
    }

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(schedule);
      observer.observe(blog);
      observer.observe(footer);
    }

    window.__gvFooterBlogGap20Recalculate = schedule;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, {
      once: true
    });
  } else {
    initialize();
  }
})();
