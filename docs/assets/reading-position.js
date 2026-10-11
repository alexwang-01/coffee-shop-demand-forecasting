// Shared by the presentation and notebook readers. Each supplies its own reading line.
function trackReadingPosition({page, navigation, content, links, sectionFor, readingLine}) {
  if (!links.length) return;
  let active = null;
  let scheduled = false;

  function update() {
    scheduled = false;
    if (page.classList.contains('hidden')) return;

    const line = readingLine();
    let selected = links[0];
    for (const link of links) {
      const section = sectionFor(link);
      if (section.getBoundingClientRect().top > line) break;
      selected = link;
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 3) {
      selected = links.at(-1);
    }
    if (selected === active) return;

    active?.classList.remove('reading-active');
    active?.removeAttribute('aria-current');
    active = selected;
    active.classList.add('reading-active');
    active.setAttribute('aria-current', 'location');

    if (!navigation.clientHeight) return;
    const box = navigation.getBoundingClientRect();
    const item = active.getBoundingClientRect();
    if (item.top < box.top + 12) navigation.scrollTop += item.top - box.top - 12;
    else if (item.bottom > box.bottom - 12) navigation.scrollTop += item.bottom - box.bottom + 12;
  }

  function schedule() {
    if (scheduled || page.classList.contains('hidden')) return;
    scheduled = true;
    requestAnimationFrame(update);
  }

  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  page.addEventListener('toggle', schedule, true);
  page.addEventListener('readerchange', schedule);
  new ResizeObserver(schedule).observe(content);
  schedule();
}
