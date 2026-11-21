(() => {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;

    button.addEventListener("click", () => {
      const showing = input.type === "password";
      input.type = showing ? "text" : "password";
      button.textContent = showing ? "🙈" : "👁️";
      button.setAttribute("aria-pressed", String(showing));
      button.setAttribute(
        "aria-label",
        showing ? "پنهان کردن رمز" : "نمایش رمز"
      );
    });
  });
})();
