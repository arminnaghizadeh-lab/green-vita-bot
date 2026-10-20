(() => {
  "use strict";

  const form = document.getElementById("gv-dx-form");
  if (!form) return;

  const input = document.getElementById("gv-dx-image");
  const drop = document.getElementById("gv-dx-drop");
  const preview = document.getElementById("gv-dx-preview");
  const fileName = document.getElementById("gv-dx-file-name");
  const uploadTitle = document.getElementById("gv-dx-upload-title");
  const uploadHelp = document.getElementById("gv-dx-upload-help");
  const modeInput = document.getElementById("gv-dx-mode");
  const notesInput = document.getElementById("gv-dx-notes");
  const submit = document.getElementById("gv-dx-submit");
  const submitLabel = submit.querySelector(".gv-dx-submit-label");
  const status = document.getElementById("gv-dx-status");
  const resultRegion = document.getElementById("gv-dx-result");
  const resultContent = document.getElementById("gv-dx-result-content");
  let previewUrl = null;
  let busy = false;

  const severityLabels = {
    none: "بدون شدت مشخص",
    mild: "خفیف",
    moderate: "متوسط",
    severe: "شدید",
    unknown: "نامشخص"
  };
  const difficultyLabels = {
    easy: "نگهداری آسان",
    medium: "نیازمند مراقبت متوسط",
    hard: "نگهداری دشوار",
    unknown: "نامشخص"
  };

  function setStatus(message, kind = "") {
    status.textContent = message || "";
    status.className = "gv-dx-status" + (kind ? ` is-${kind}` : "");
  }

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function setMode(mode) {
    modeInput.value = mode;
    document.querySelectorAll(".gv-dx-mode").forEach(button => {
      const active = button.dataset.mode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    submitLabel.textContent = mode === "identify"
      ? "شناسایی نوع گیاه"
      : "شروع تشخیص آنلاین";
    notesInput.placeholder = mode === "identify"
      ? "شرایط نور، آبیاری یا سؤالت درباره نگهداری گیاه را بنویس."
      : "از چه زمانی این مشکل شروع شده؟ آبیاری و نور گیاه چطور است؟";
  }

  document.querySelectorAll(".gv-dx-mode").forEach(button => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  function showFile(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      input.value = "";
      setStatus("لطفاً یک فایل تصویری انتخاب کن.", "error");
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      input.value = "";
      setStatus("حجم عکس اصلی باید کمتر از ۱۵ مگابایت باشد.", "error");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    fileName.textContent = file.name;
    uploadTitle.textContent = "عکس انتخاب شد";
    uploadHelp.textContent = "برای انتخاب عکس دیگری کلیک کن.";
    setStatus("");
  }

  input.addEventListener("change", () => showFile(input.files[0]));

  ["dragenter", "dragover"].forEach(type => {
    drop.addEventListener(type, event => {
      event.preventDefault();
      drop.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach(type => {
    drop.addEventListener(type, event => {
      event.preventDefault();
      drop.classList.remove("is-dragging");
    });
  });
  drop.addEventListener("drop", event => {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    showFile(file);
  });

  function loadImage(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        URL.revokeObjectURL(url);
        resolve(image);
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("بازکردن این تصویر ممکن نیست؛ عکس دیگری امتحان کن."));
      };
      image.src = url;
    });
  }

  async function toJpeg(file) {
    let source;
    let closeSource = false;

    try {
      if ("createImageBitmap" in window) {
        source = await createImageBitmap(file);
        closeSource = true;
      } else {
        source = await loadImage(file);
      }
    } catch (_) {
      source = await loadImage(file);
    }

    const sw = source.width;
    const sh = source.height;
    if (!sw || !sh) {
      if (closeSource) source.close();
      throw new Error("ابعاد عکس قابل تشخیص نیست.");
    }

    const ratio = Math.min(1, 1600 / Math.max(sw, sh));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(sw * ratio));
    canvas.height = Math.max(1, Math.round(sh * ratio));
    const context = canvas.getContext("2d");
    if (!context) {
      if (closeSource) source.close();
      throw new Error("مرورگر نتوانست عکس را آماده کند.");
    }

    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    if (closeSource) source.close();

    const encode = quality => new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (blob) resolve(blob);
        else reject(new Error("تبدیل عکس انجام نشد؛ لطفاً عکس دیگری انتخاب کن."));
      }, "image/jpeg", quality);
    });

    let blob = await encode(0.84);
    if (blob.size > 8 * 1024 * 1024) blob = await encode(0.68);
    canvas.width = 1;
    canvas.height = 1;

    if (blob.size > 8 * 1024 * 1024) {
      throw new Error("حجم عکس پس از فشرده‌سازی هنوز زیاد است؛ عکس دیگری انتخاب کن.");
    }
    return blob;
  }

  function addCard(parent, title, value) {
    if (value === undefined || value === null || value === "") return;
    const values = Array.isArray(value)
      ? value.filter(v => v !== undefined && v !== null && String(v).trim())
      : [value];
    if (!values.length) return;

    const card = make("section", "gv-dx-result-card");
    card.appendChild(make("h3", "", title));

    if (Array.isArray(value)) {
      const list = make("ul");
      values.forEach(item => list.appendChild(make("li", "", item)));
      card.appendChild(list);
    } else {
      card.appendChild(make("p", "", value));
    }
    parent.appendChild(card);
  }

  function addConfidence(parent, confidence) {
    const score = Math.max(0, Math.min(100, Number(confidence) || 0));
    const wrapper = make("div", "gv-dx-confidence");
    wrapper.appendChild(make("div", "", `میزان اطمینان تخمینی مدل: ${score}٪`));
    const meter = make("div", "gv-dx-meter");
    const fill = make("span");
    fill.style.width = `${score}%`;
    meter.appendChild(fill);
    wrapper.appendChild(meter);
    parent.appendChild(wrapper);
  }

  function renderResult(mode, data) {
    resultContent.replaceChildren();

    const summary = make("div", "gv-dx-summary");
    const grid = make("div", "gv-dx-result-grid");

    if (mode === "diagnose") {
      summary.appendChild(make("h3", "", data.is_healthy ? "گیاه احتمالاً سالم است" : (data.disease_name || "نتیجه تشخیص")));
      summary.appendChild(make("span", "gv-dx-badge", `شدت: ${severityLabels[data.severity] || "نامشخص"}`));
      if (data.is_healthy) {
        summary.appendChild(make("p", "", "بر اساس این تصویر، نشانه قطعی از بیماری گزارش نشده است."));
      }
      addConfidence(summary, data.confidence);
      resultContent.appendChild(summary);
      addCard(grid, "علائم مشاهده‌شده", data.symptoms);
      addCard(grid, "علت‌های احتمالی", data.cause);
      addCard(grid, "اقدامات و درمان پیشنهادی", data.treatment);
      addCard(grid, "پیشگیری و مراقبت بعدی", data.prevention);
    } else {
      summary.appendChild(make("h3", "", data.persian_name || "نام گیاه مشخص نشد"));
      if (data.scientific_name) {
        const scientific = make("p", "");
        scientific.dir = "ltr";
        scientific.style.textAlign = "right";
        scientific.textContent = data.scientific_name;
        summary.appendChild(scientific);
      }
      summary.appendChild(make("span", "gv-dx-badge", difficultyLabels[data.difficulty_level] || "سطح نگهداری نامشخص"));
      if (data.is_plant === false) {
        summary.appendChild(make("p", "", "تصویر برای شناسایی گیاه کافی نبود؛ عکس واضح‌تری از برگ‌ها و شکل کلی گیاه ارسال کن."));
      }
      addConfidence(summary, data.confidence);
      resultContent.appendChild(summary);

      addCard(grid, "نور مناسب", data.light_requirement);
      addCard(grid, "برنامه آبیاری", data.watering_schedule);
      addCard(grid, "رطوبت مناسب", data.humidity);
      addCard(grid, "دمای مناسب", data.temperature);
      addCard(grid, "خاک پیشنهادی", data.soil_mix);
      addCard(grid, "توصیه کوددهی", data.fertilizer_recommendation);
      addCard(grid, "گلدان و کاشت", data.potting_advice);
      addCard(grid, "زمان تعویض گلدان", data.repotting_interval);
      addCard(grid, "روش‌های تکثیر", data.propagation_methods);
      addCard(grid, "آفات رایج", data.common_pests);
      addCard(grid, "بیماری‌های رایج", data.common_diseases);
      addCard(grid, "سمیت برای حیوانات خانگی", data.toxicity_pets);
      addCard(grid, "سمیت برای انسان", data.toxicity_humans);
      addCard(grid, "نکات پیشگیرانه", data.preventive_care_tips);
    }

    if (grid.childElementCount) resultContent.appendChild(grid);
    if (data.parse_succeeded === false) {
      resultContent.appendChild(make("p", "gv-dx-disclaimer",
        "پاسخ ساختاریافته کامل دریافت نشد؛ برای نتیجه مطمئن‌تر، عکس واضح‌تری ارسال کن."));
    }
    resultRegion.hidden = false;
    resultRegion.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;

    const file = input.files[0];
    if (!file) {
      setStatus("اول عکس گیاه را انتخاب کن.", "error");
      return;
    }

    busy = true;
    submit.disabled = true;
    submitLabel.textContent = "در حال آماده‌سازی و بررسی عکس…";
    resultRegion.hidden = true;
    setStatus("عکس در حال آماده‌شدن است؛ ممکن است تحلیل کمی طول بکشد.");

    try {
      const jpeg = await toJpeg(file);
      const body = new FormData(form);
      body.set("image", new File([jpeg], "plant-photo.jpg", { type: "image/jpeg" }));

      submitLabel.textContent = "هوش مصنوعی در حال بررسی گیاه است…";
      const response = await fetch("/diagnosis/api/analyze", {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      let payload;
      try {
        payload = await response.json();
      } catch (_) {
        throw new Error("پاسخ معتبری از سرور دریافت نشد؛ دوباره تلاش کن.");
      }
      if (!response.ok || !payload.ok) {
        throw new Error(payload.detail || "تحلیل انجام نشد؛ لطفاً دوباره تلاش کن.");
      }

      renderResult(payload.mode, payload.result);
      setStatus("تحلیل انجام شد.", "success");
    } catch (error) {
      setStatus(error?.message || "ارتباط با سرویس تشخیص برقرار نشد.", "error");
    } finally {
      busy = false;
      submit.disabled = false;
      submitLabel.textContent = modeInput.value === "identify"
        ? "شناسایی نوع گیاه"
        : "شروع تشخیص آنلاین";
    }
  });

  window.addEventListener("beforeunload", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
})();
