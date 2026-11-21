(() => {
  const form = document.getElementById("gv-account-register-form");
  if (!form) return;

  const fa = "۰۱۲۳۴۵۶۷۸۹";
  const ar = "٠١٢٣٤٥٦٧٨٩";
  function normalizeDigits(value) {
    return String(value || "").replace(/[۰-۹٠-٩]/g, ch => {
      const i = fa.indexOf(ch);
      return String(i >= 0 ? i : ar.indexOf(ch));
    });
  }

  function validName(value) {
    const name = String(value || "").replace(/\s+/g, " ").trim();
    const letters = name.replace(/[\s‌]/g, "");
    return letters.length >= 3 && /^[آ-یءٔ‌ ]+$/.test(name);
  }

  function validPhone(value) {
    return /^09\d{9}$/.test(normalizeDigits(value));
  }

  const rules = [
    { id: "first_name", errorId: "gv-register-error-first_name", validate: validName },
    { id: "last_name", errorId: "gv-register-error-last_name", validate: validName },
    { id: "phone_number", errorId: "gv-register-error-phone_number", validate: validPhone }
  ];

  function check(rule, force = false) {
    const input = document.getElementById(rule.id);
    const group = input?.closest(".gv-account-field");
    if (!input || !group) return true;

    if (!force && input.dataset.gvTouched !== "1" && input.value === "") {
      group.classList.remove("gv-field-invalid", "gv-field-valid");
      input.setAttribute("aria-invalid", "false");
      return true;
    }

    const valid = rule.validate(input.value);
    group.classList.toggle("gv-field-invalid", !valid);
    group.classList.toggle("gv-field-valid", valid && input.value.trim() !== "");
    input.setAttribute("aria-invalid", valid ? "false" : "true");
    input.setAttribute("aria-describedby", rule.errorId);
    return valid;
  }

  rules.forEach(rule => {
    const input = document.getElementById(rule.id);
    if (!input) return;
    input.addEventListener("input", () => {
      input.dataset.gvTouched = "1";
      check(rule);
    });
    input.addEventListener("blur", () => {
      input.dataset.gvTouched = "1";
      check(rule);
    });
    input.addEventListener("invalid", () => {
      input.dataset.gvTouched = "1";
      check(rule, true);
    });
    if (input.value !== "") {
      input.dataset.gvTouched = "1";
      check(rule);
    }
  });

  form.addEventListener("submit", event => {
    let firstInvalid = null;
    rules.forEach(rule => {
      if (!check(rule, true) && !firstInvalid) {
        firstInvalid = document.getElementById(rule.id);
      }
    });
    if (firstInvalid) {
      event.preventDefault();
      firstInvalid.focus();
    }
  });
})();
