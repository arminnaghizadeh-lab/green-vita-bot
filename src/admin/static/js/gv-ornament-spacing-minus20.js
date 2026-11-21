/* GV ORNAMENT SPACING MINUS 20 — PERMANENT V1 */
(() => {
  if (window.__gvOrnamentSpacingMinus20Installed) return;
  window.__gvOrnamentSpacingMinus20Installed = true;

  const TARGET = -20;
  const IMAGE_SELECTOR = ".gv-home-middle-ornament";
  const BEFORE_CLASS = "gv-ornament-flow-before-v1";
  const AFTER_CLASS = "gv-ornament-flow-after-v1";

  let resizeTimer = null;

  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
      s.display !== "none" && s.visibility !== "hidden";
  };

  const contentChildren = section =>
    [...section.children].filter(el => {
      const cls = typeof el.className === "string" ? el.className : "";
      return !el.classList.contains("gv-home-middle-ornament") &&
        !el.classList.contains(BEFORE_CLASS) &&
        !el.classList.contains(AFTER_CLASS) &&
        !["SCRIPT", "STYLE"].includes(el.tagName) &&
        visible(el);
    });

  const lastContent = section => contentChildren(section).at(-1);
  const firstContent = section => contentChildren(section)[0];

  function makeSpacer(img, cls, before) {
    let spacer = before ? img.previousElementSibling : img.nextElementSibling;

    if (!spacer || !spacer.classList.contains(cls)) {
      spacer = document.createElement("div");
      spacer.className = cls;
      spacer.setAttribute("aria-hidden", "true");

      if (before) img.parentNode.insertBefore(spacer, img);
      else img.parentNode.insertBefore(spacer, img.nextSibling);
    }

    spacer.style.setProperty("display", "block", "important");
    spacer.style.setProperty("width", "100%", "important");
    spacer.style.setProperty("box-sizing", "border-box", "important");
    spacer.style.setProperty("line-height", "0", "important");
    spacer.style.setProperty("font-size", "0", "important");
    spacer.style.setProperty("overflow", "hidden", "important");
    spacer.style.setProperty("visibility", "hidden", "important");
    spacer.style.setProperty("pointer-events", "none", "important");
    return spacer;
  }

  function setFlow(spacer, value) {
    const v = Number(value.toFixed(3));
    const h = Math.max(0, v);
    const m = Math.min(0, v);

    spacer.dataset.gvFlow = String(v);
    spacer.style.setProperty("height", `${h}px`, "important");
    spacer.style.setProperty("min-height", `${h}px`, "important");
    spacer.style.setProperty("max-height", `${h}px`, "important");
    spacer.style.setProperty("flex", `0 0 ${h}px`, "important");
    spacer.style.setProperty("margin-top", "0px", "important");
    spacer.style.setProperty("margin-bottom", `${m}px`, "important");
  }

  const flowValue = spacer => Number(spacer.dataset.gvFlow || 0);

  function getGap(img, sections) {
    const section = img.parentElement;
    const index = sections.indexOf(section);

    if (index < 1) throw new Error("بخش قبلی Ornament پیدا نشد.");

    const previous = lastContent(sections[index - 1]);
    const next = firstContent(section);

    if (!previous || !next) {
      throw new Error("محتوای مجاور Ornament پیدا نشد.");
    }

    const a = previous.getBoundingClientRect();
    const b = img.getBoundingClientRect();
    const c = next.getBoundingClientRect();

    return {
      before: b.top - a.bottom,
      after: c.top - b.bottom
    };
  }

  function protectedSnapshot(sections) {
    const bot = document.querySelector("#green-vita-bots")
      || document.querySelector("section.gv-bot-promo");
    const blog = document.querySelector("#blog");
    const footer = document.querySelector(".gv-footer");

    const botIndex = sections.indexOf(bot);
    const botPrev = sections[botIndex - 1];
    const botNext = sections[botIndex + 1];
    const blogLast = blog && lastContent(blog);

    if (!bot || !blog || !footer || !botPrev || !botNext || !blogLast) {
      throw new Error("بخش محافظت‌شده ربات یا فوتر پیدا نشد.");
    }

    return {
      botBefore: bot.getBoundingClientRect().top -
        botPrev.getBoundingClientRect().bottom,
      botAfter: botNext.getBoundingClientRect().top -
        bot.getBoundingClientRect().bottom,
      footerAbove: footer.getBoundingClientRect().top -
        blog.getBoundingClientRect().bottom,
      footerFromBlogContent: footer.getBoundingClientRect().top -
        blogLast.getBoundingClientRect().bottom
    };
  }

  function run() {
    const images = [...document.querySelectorAll(IMAGE_SELECTOR)];
    const sections = [...document.querySelectorAll("section")];

    if (images.length !== 7) {
      console.error("GV Ornament: تعداد تصاویر ۷ نیست؛ تغییری اعمال نشد.", images.length);
      return;
    }

    try {
      const pairs = images.map(img => ({
        img,
        before: makeSpacer(img, BEFORE_CLASS, true),
        after: makeSpacer(img, AFTER_CLASS, false)
      }));

      // شروع هر بار از وضعیت خنثی؛ جلوگیری از جمع‌شدن تغییرات در Resize
      pairs.forEach(({ before, after }) => {
        setFlow(before, 0);
        setFlow(after, 0);
      });

      const protectedBefore = protectedSnapshot(sections);

      for (const pair of pairs) {
        const { img, before, after } = pair;

        // تنظیم تکراری برای جبران رفتار واقعی جریان بلوکی و حاشیه‌ها
        for (let pass = 0; pass < 6; pass++) {
          const g1 = getGap(img, sections);
          setFlow(before, flowValue(before) - (g1.before - TARGET));

          const g2 = getGap(img, sections);
          setFlow(after, flowValue(after) - (g2.after - TARGET));
        }
      }

      const results = pairs.map(({ img }, i) => {
        const g = getGap(img, sections);
        return {
          ornament: i + 1,
          before: +g.before.toFixed(1),
          after: +g.after.toFixed(1),
          difference: +Math.abs(g.before - g.after).toFixed(1)
        };
      });

      const protectedAfter = protectedSnapshot(sections);

      const spacingOK = results.every(x =>
        Math.abs(x.before - TARGET) <= 1.5 &&
        Math.abs(x.after - TARGET) <= 1.5
      );

      const protectedOK = Object.keys(protectedBefore).every(key =>
        Math.abs(protectedBefore[key] - protectedAfter[key]) <= 1.5
      );

      if (!spacingOK || !protectedOK) {
        pairs.forEach(({ before, after }) => {
          setFlow(before, 0);
          setFlow(after, 0);
        });

        console.error(
          "GV Ornament: اعتبارسنجی ناموفق؛ فاصله‌گذارها به حالت خنثی برگشتند."
        );
        console.table(results);
        return;
      }

      console.log("GV Ornament: فاصله‌گذاری دائمی -20px فعال شد.");
      console.table(results);
      console.log("فاصله‌های اطراف ربات و بالای فوتر حفظ شدند.");

    } catch (error) {
      console.error("GV Ornament spacing error:", error);
    }
  }

  function schedule() {
    requestAnimationFrame(() => requestAnimationFrame(run));
  }

  if (document.readyState === "complete") {
    schedule();
  } else {
    window.addEventListener("load", schedule, { once: true });
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(schedule);
  }

  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(schedule, 200);
  }, { passive: true });

  window.__gvOrnamentSpacingReflow = schedule;
})();
