// One result horizon controls all downstream chapters. Teaching controls are independent.
function readerOffset(target) {
  let offset = document.querySelector('.topbar').getBoundingClientRect().height;
  const page = target.closest('#forecasting, #data');
  if (matchMedia('(max-width:1000px)').matches) offset += 45;
  if (target.closest('.forecast-results-region')) {
    offset += page.querySelector('.forecast-switchbar').getBoundingClientRect().height;
  }
  return offset + 16;
}

function scrollToReaderTarget(target, behavior = 'smooth') {
  const toc = target.closest('#forecasting, #data').querySelector('.notebook-toc');
  toc.classList.remove('toc-expanded');
  toc.querySelector('.toc-toggle')?.setAttribute('aria-expanded', 'false');
  window.scrollTo({top: window.scrollY + target.getBoundingClientRect().top - readerOffset(target), behavior});
}

function setupReaderToc(page) {
  const toc = page.querySelector('.notebook-toc');
  if (!toc.querySelector('.toc-toggle')) {
    const links = document.createElement('div');
    links.className = 'toc-links';
    links.append(...toc.childNodes);
    const button = document.createElement('button');
    button.className = 'toc-toggle';
    button.setAttribute('aria-expanded', 'false');
    button.textContent = 'Chapters ⌄';
    toc.append(button, links);
  }
  const button = toc.querySelector('.toc-toggle');
  button.onclick = () => {
    const open = toc.classList.toggle('toc-expanded');
    button.setAttribute('aria-expanded', String(open));
  };
  toc.querySelectorAll('[data-nb-target]').forEach(link => {
    link.onclick = event => {
      event.preventDefault();
      const target = document.getElementById(link.dataset.nbTarget);
      if (target) scrollToReaderTarget(target);
    };
  });
}

function setupForecastSwitch() {
  const page = document.getElementById('forecasting');
  const region = page.querySelector('.forecast-results-region');
  const bar = page.querySelector('.forecast-switchbar');
  let current = 'monthly';
  window.setForecastHorizon = (horizon, keepPosition = true) => {
    if (!['weekly', 'monthly'].includes(horizon) || horizon === current) return;
    const old = page.querySelector(`.forecast-variant[data-horizon="${current}"]`);
    const next = page.querySelector(`.forecast-variant[data-horizon="${horizon}"]`);
    const line = readerOffset(old);
    const pastSwitch = region.getBoundingClientRect().top < document.querySelector('.topbar').getBoundingClientRect().bottom;
    const chapters = [...old.querySelectorAll('.forecast-chapter')];
    // Prefer a chapter heading already visible in the upper reading area over
    // the tail of the previous chapter (for example its chart legend).
    const headingWindow = Math.min(360, (innerHeight - line) * .7);
    const chapter = chapters.filter(c => c.getBoundingClientRect().top <= line + headingWindow).at(-1) || chapters[0];
    const progress = Math.max(0, line - chapter.getBoundingClientRect().top);
    // Preserve the item and category, while each version supplies its own model label.
    const oldItem = old.querySelector('.forecast-item');
    const nextType = next.querySelector('.forecast-type');
    nextType.value = old.querySelector('.forecast-type').value;
    nextType.dispatchEvent(new Event('change'));
    const nextItem = next.querySelector('.forecast-item');
    if ([...nextItem.options].some(o => o.value === oldItem.value)) {
      nextItem.value = oldItem.value;
      nextItem.dispatchEvent(new Event('change'));
    }
    old.hidden = true; next.hidden = false; current = horizon;
    page.dataset.forecastHorizon = horizon;
    bar.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.forecastHorizon === horizon)));
    page.querySelectorAll('.notebook-toc [data-chapter]').forEach(link => {
      const n = Number(link.dataset.chapter);
      const id = n < 4 ? `forecast-section-${n}` : `forecast-${horizon}-section-${n}`;
      link.dataset.nbTarget = id; link.setAttribute('href', '#' + id);
    });
    if (keepPosition && pastSwitch) {
      const target = next.querySelector(`[data-chapter="${chapter.dataset.chapter}"]`);
      const offset = Math.min(progress, Math.max(0, target.offsetHeight - 150));
      // Hidden figures acquire their layout when the result pane becomes visible.
      // Scroll after that layout instead of letting browser anchoring move the reader.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        window.scrollTo({top: window.scrollY + target.getBoundingClientRect().top + offset - readerOffset(target), behavior:'instant'});
        page.dispatchEvent(new Event('readerchange'));
      }));
    }
    page.dispatchEvent(new Event('readerchange'));
  };
  bar.querySelectorAll('button').forEach(button => {
    button.onclick = () => window.setForecastHorizon(button.dataset.forecastHorizon);
  });
  page.dataset.forecastHorizon = current;
}
