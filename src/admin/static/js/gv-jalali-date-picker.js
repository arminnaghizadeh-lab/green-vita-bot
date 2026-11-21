(function () {
  'use strict';
  if (window.gvJalaliDatePickerLoaded) return;
  window.gvJalaliDatePickerLoaded = true;

  const digits = '۰۱۲۳۴۵۶۷۸۹';
  const months = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
  const weekdays = ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'];
  const formatter = new Intl.DateTimeFormat('en-US-u-ca-persian-nu-latn', {
    year:'numeric', month:'numeric', day:'numeric'
  });
  const pad = n => String(n).padStart(2, '0');
  const fa = v => String(v).replace(/\d/g, d => digits[Number(d)]);
  const isoOf = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;

  function dateOf(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || '').trim());
    if (!m) return null;
    const d = new Date(+m[1], +m[2]-1, +m[3]);
    return d.getFullYear() === +m[1] && d.getMonth() === +m[2]-1 && d.getDate() === +m[3] ? d : null;
  }

  function parts(d) {
    const p = Object.fromEntries(formatter.formatToParts(d)
      .filter(x => x.type !== 'literal').map(x => [x.type, Number(x.value)]));
    return { y:p.year, m:p.month, d:p.day };
  }

  function display(iso) {
    const d = dateOf(iso);
    if (!d) return String(iso || '');
    const p = parts(d);
    return `${fa(p.y)}/${fa(pad(p.m))}/${fa(pad(p.d))}`;
  }

  window.gvFormatJalaliDate = display;
  window.gvGetISODate = input => input?.dataset?.isoValue || input?.value || '';

  function firstOfMonth(anchor, year, month) {
    for (let n = -40; n <= 40; n++) {
      const d = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()+n);
      const p = parts(d);
      if (p.y === year && p.m === month && p.d === 1) return d;
    }
    return anchor;
  }

  let active = null, viewDate = null, popup = null;

  function close() {
    popup?.remove();
    active?.setAttribute('aria-expanded', 'false');
    popup = active = null;
  }

  function position() {
    if (!popup || !active) return;
    const r = active.getBoundingClientRect();
    popup.style.top = `${Math.max(8, Math.min(innerHeight-330, r.bottom+7))}px`;
    popup.style.left = `${Math.max(8, Math.min(innerWidth-300, r.left))}px`;
  }

  function render() {
    if (!popup || !active) return;
    const p = parts(viewDate);
    const first = firstOfMonth(viewDate, p.y, p.m);
    const offset = (first.getDay()+1)%7;
    const start = new Date(first.getFullYear(), first.getMonth(), first.getDate()-offset);
    const selected = active.dataset.isoValue;
    const today = isoOf(new Date());
    const cells = [];

    for (let i=0; i<42; i++) {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate()+i);
      const jp = parts(d), iso = isoOf(d);
      const cls = [
        'gv-jdp-day',
        jp.y !== p.y || jp.m !== p.m ? 'is-outside' : '',
        iso === selected ? 'is-selected' : '',
        iso === today ? 'is-today' : ''
      ].filter(Boolean).join(' ');
      cells.push(`<button type="button" class="${cls}" data-iso="${iso}">${fa(jp.d)}</button>`);
    }

    popup.innerHTML = `
      <div class="gv-jdp-head">
        <button type="button" class="gv-jdp-nav" data-step="-1">‹</button>
        <strong>${months[p.m-1]} ${fa(p.y)}</strong>
        <button type="button" class="gv-jdp-nav" data-step="1">›</button>
      </div>
      <div class="gv-jdp-week">${weekdays.map(x=>`<span>${x}</span>`).join('')}</div>
      <div class="gv-jdp-grid">${cells.join('')}</div>
      <div class="gv-jdp-foot">
        <button type="button" data-today>امروز</button>
        <button type="button" data-close>بستن</button>
      </div>`;
  }

  function selectDate(iso) {
    if (!active) return;
    active.dataset.isoValue = iso;
    active.value = display(iso);
    const hidden = active.dataset.gvIsoTarget &&
      document.getElementById(active.dataset.gvIsoTarget);
    if (hidden) hidden.value = iso;
    active.dispatchEvent(new Event('change', {bubbles:true}));
    close();
  }

  function open(input) {
    if (active === input) return close();
    close();
    active = input;
    viewDate = dateOf(input.dataset.isoValue) || new Date();
    popup = document.createElement('div');
    popup.className = 'gv-jalali-picker';
    popup.setAttribute('dir','rtl');
    document.body.appendChild(popup);
    input.setAttribute('aria-expanded','true');
    render();
    position();
  }

  document.addEventListener('click', event => {
    const input = event.target.closest('[data-gv-jalali-date]');
    if (input) {
      event.preventDefault();
      open(input);
      return;
    }

    if (popup && popup.contains(event.target)) {
      const step = event.target.closest('[data-step]');
      const day = event.target.closest('[data-iso]');
      if (step) {
        const p = parts(viewDate);
        const m0 = p.m + Number(step.dataset.step);
        const y = p.y + (m0 < 1 ? -1 : m0 > 12 ? 1 : 0);
        const m = m0 < 1 ? 12 : m0 > 12 ? 1 : m0;
        viewDate = firstOfMonth(viewDate, y, m);
        render();
      } else if (day) {
        selectDate(day.dataset.iso);
      } else if (event.target.closest('[data-today]')) {
        selectDate(isoOf(new Date()));
      } else if (event.target.closest('[data-close]')) {
        close();
      }
      return;
    }
    if (popup) close();
  });

  addEventListener('resize', position);
  addEventListener('scroll', position, true);

  document.querySelectorAll('[data-gv-date-display]').forEach(el => {
    el.textContent = display(el.dataset.gvDateDisplay);
  });

  document.querySelectorAll('[data-gv-jalali-date]').forEach(input => {
    const iso = input.value || input.dataset.isoValue || '';
    input.dataset.isoValue = iso;
    input.value = display(iso);
    input.readOnly = true;
    input.autocomplete = 'off';
    input.placeholder = 'انتخاب تاریخ شمسی';
    input.setAttribute('aria-haspopup','dialog');
    input.setAttribute('aria-expanded','false');
  });
})();