(function () {
  const key = "agri-trust-theme";
  const root = document.documentElement;

  function currentTheme() {
    return root.dataset.theme === "light" ? "light" : "dark";
  }

  function applyTheme(theme) {
    const normalized = theme === "light" ? "light" : "dark";
    root.dataset.theme = normalized;
    localStorage.setItem(key, normalized);
    document.querySelectorAll("[data-theme-label]").forEach((item) => {
      item.textContent = normalized === "light" ? "Light" : "Dark";
    });
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", normalized === "light" ? "true" : "false");
      button.setAttribute("title", normalized === "light" ? "切换到 Dark" : "切换到 Light");
    });
  }

  applyTheme(localStorage.getItem(key) || currentTheme());

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(currentTheme());
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        applyTheme(currentTheme() === "light" ? "dark" : "light");
      });
    });
  });
})();
