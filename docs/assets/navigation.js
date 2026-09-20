const $ = id => document.getElementById(id);
function route() {
  const pages = ['overview', 'materials', 'data', 'forecasting'];
  const hash = location.hash.slice(1);
  const requested = hash === 'walkthrough' ? 'data' : hash === 'forecasting-weekly' ? 'forecasting' : hash;
  const view = pages.includes(requested) ? requested : 'overview';
  for (const name of pages) {
    $(name).classList.toggle('hidden', name !== view);
    $('nav-' + name).classList.toggle('active', name === view);
    if (name === view) $('nav-' + name).setAttribute('aria-current', 'page');
    else $('nav-' + name).removeAttribute('aria-current');
  }
  if (hash === 'forecasting-weekly') window.setForecastHorizon?.('weekly', false);
  window.scrollTo({top:0, behavior:'instant'});
}
async function loadNotebook() {
  try {
    const [forecast, eda] = await Promise.all([
      fetch('content/forecasting/notebook.html'),
      fetch('content/eda/notebook.html'),
    ]);
    if (!forecast.ok || !eda.ok) throw new Error('Notebook output is unavailable.');
    $('notebook').innerHTML = await forecast.text();
    $('data-notebook').innerHTML = await eda.text();
    setupSectionCards();
    setupItemForecasts(); setupMethodDemo(); setupForecastSwitch();
    for (const id of ['data','forecasting']) {
      setupReaderToc($(id)); setupReadingPosition($(id));
    }
    $('status').textContent = '';
    route();
  } catch (error) {
    $('status').textContent = 'Unable to load analysis: ' + error.message;
    $('status').className = 'error';
  }
}
window.addEventListener('hashchange', route);
route(); loadNotebook();

function groupByHeading(container, headingSelector, cardClass) {
  if (!container || container.dataset.cardsReady) return;
  container.dataset.cardsReady = 'true';
  let card = null;
  [...container.children].forEach(node => {
    if (node.matches(headingSelector)) {
      card = document.createElement('section');
      card.className = cardClass;
      node.before(card);
    }
    if (card) card.append(node);
  });
}

function setupSectionCards() {
  groupByHeading(document.querySelector('#materials'), 'h2', 'bom-section');
  groupByHeading(document.querySelector('#data .notebook-body'), '.notebook-part', 'analysis-card');
}

function setupItemForecasts() {
  document.querySelectorAll('.item-forecast-explorer').forEach(explorer => {
    if (explorer.dataset.initialized) return;
    explorer.dataset.initialized = 'true';
    const category = explorer.querySelector('.forecast-type');
    const item = explorer.querySelector('.forecast-item');
    const options = [...item.options];
    const show = () => explorer.querySelectorAll('.item-forecast-panel').forEach(panel => {
      panel.hidden = panel.dataset.item !== item.value;
    });
    const filter = () => {
      const current = item.value;
      item.replaceChildren(...options.filter(option => option.dataset.kind === category.value));
      if ([...item.options].some(option => option.value === current)) item.value = current;
      show();
    };
    category.addEventListener('change', filter);
    item.addEventListener('change', show);
    filter();
  });
}

function setupMethodDemo() {
  document.querySelectorAll('.method-demo').forEach(demo => {
    if (demo.dataset.initialized) return;
    demo.dataset.initialized = 'true';
    const scenario = demo.querySelector('.demo-scenario');
    const model = demo.querySelector('.demo-model');
    const horizon = demo.querySelector('.demo-horizon');
    const update = () => demo.querySelectorAll('.method-demo-panel').forEach(panel => {
      panel.hidden = panel.dataset.scenario !== scenario.value || panel.dataset.model !== model.value || (horizon && panel.dataset.horizon !== horizon.value);
    });
    let measuredWidth = 0;
    const sizeExplanations = () => {
      const width = demo.getBoundingClientRect().width;
      if (!width || width === measuredWidth) return;
      measuredWidth = width;
      let tallest = 0;
      demo.querySelectorAll('.method-explanation').forEach(explanation => {
        const probe = explanation.cloneNode(true);
        probe.setAttribute('aria-hidden', 'true');
        Object.assign(probe.style, {
          position: 'absolute', visibility: 'hidden', pointerEvents: 'none',
          width: width + 'px', minHeight: '0', height: 'auto'
        });
        demo.appendChild(probe);
        tallest = Math.max(tallest, probe.getBoundingClientRect().height);
        probe.remove();
      });
      demo.style.setProperty('--explanation-height', Math.ceil(tallest) + 'px');
    };
    new ResizeObserver(sizeExplanations).observe(demo);
    document.fonts.ready.then(() => { measuredWidth = 0; sizeExplanations(); });
    scenario.addEventListener('change', update);
    model.addEventListener('change', update);
    horizon?.addEventListener('change', update);
    update();
  });
}

