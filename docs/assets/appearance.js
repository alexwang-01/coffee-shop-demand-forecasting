// Theme preference and walkthrough reading position.
const themeButton = $('theme-toggle');

function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  themeButton.innerHTML = dark ?
    '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>' :
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14A9 9 0 0 1 10 3.5 9 9 0 1 0 20.5 14Z"/></svg>';
  themeButton.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
  themeButton.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
  themeButton.setAttribute('aria-pressed', String(dark))
}
themeButton.onclick = () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem('coffee-theme', next)
  } catch (e) {}
  updateThemeButton()
};
updateThemeButton();
new ResizeObserver(entries => document.documentElement.style.setProperty('--header-height', entries[
  0].target.offsetHeight + 'px')).observe(document.querySelector('.topbar'));

function setupReadingPosition(page) {
  const toc = page.querySelector('.notebook-toc');
  const links = [...toc.querySelectorAll('[data-nb-target]')];

  let active = -1,
    scheduled = false;

  function update() {
    scheduled = false;
    if (page.classList.contains('hidden')) return;
    const headerBottom = document.querySelector('.topbar').getBoundingClientRect().bottom;
    const mobile = window.matchMedia('(max-width:1000px)').matches;
    const bar = page.querySelector('.forecast-switchbar');
    const pinned = bar && bar.getBoundingClientRect().top <= headerBottom + (mobile ? 45 : 0) + 1;
    const readingLine = headerBottom + (mobile ? 45 : 0) + (pinned ? bar.offsetHeight : 0) + 32;
    const sections = links.map(a => document.getElementById(a.dataset.nbTarget));
    let index = 0;
    for (let i = 0; i < sections.length; i++) {
      if (sections[i].getBoundingClientRect().top <= readingLine) index = i;
      else break
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 3) index =
      sections.length - 1;
    if (index === active) return;
    active = index;
    links.forEach((a, i) => {
      a.classList.toggle('reading-active', i === index);
      if (i === index) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current')
    });
    const link = links[index],
      box = toc.getBoundingClientRect(),
      item = link.getBoundingClientRect();
    if (item.top < box.top + 12) toc.scrollTop += item.top - box.top - 12;
    else if (item.bottom > box.bottom - 12) toc.scrollTop += item.bottom - box.bottom + 12;
  }

  function schedule() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(update)
    }
  }
  window.addEventListener('scroll', schedule, {
    passive: true
  });
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  page.addEventListener('toggle', schedule, true);
  page.addEventListener('readerchange', () => { active = -1; schedule(); });
  new ResizeObserver(schedule).observe(page.querySelector('.notebook-body'));
  schedule();
}
