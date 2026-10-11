// Theme preference and the shared sticky-header height.
(() => {
  const themeButton = document.getElementById('theme-toggle');

  function updateThemeButton() {
    const dark = document.documentElement.dataset.theme === 'dark';
    themeButton.innerHTML = dark ?
      '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>' :
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14A9 9 0 0 1 10 3.5 9 9 0 1 0 20.5 14Z"/></svg>';
    const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
    themeButton.title = label;
    themeButton.setAttribute('aria-label', label);
    themeButton.setAttribute('aria-pressed', String(dark));
  }

  themeButton.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem('coffee-theme', next);
    } catch {
      // Theme switching still works when browser storage is unavailable.
    }
    updateThemeButton();
  });

  updateThemeButton();
  new ResizeObserver(([entry]) => {
    document.documentElement.style.setProperty('--header-height', entry.target.offsetHeight + 'px');
  }).observe(document.querySelector('.topbar'));
})();
