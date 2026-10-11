// Load the slide document once; scrolling is shared with the analysis readers.
(() => {
  const page = document.getElementById('presentation');
  if (!page) return;
  let loading;

  function createContents(slides, navigation) {
    return slides.map((slide, index) => {
      if (slide.dataset.group) {
        const heading = document.createElement('p');
        heading.className = 'deck-nav-group';
        heading.textContent = slide.dataset.group;
        navigation.append(heading);
      }

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'deck-nav-item';
      button.textContent = (index + 1) + '. ' + (slide.dataset.navTitle || slide.dataset.title);
      button.setAttribute('aria-label', 'Slide ' + (index + 1) + ': ' + slide.dataset.title);
      button.setAttribute('aria-controls', slide.id);
      button.addEventListener('click', () => {
        const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
        slide.scrollIntoView({block: 'start', behavior: reducedMotion ? 'instant' : 'smooth'});
      });
      navigation.append(button);
      return button;
    });
  }

  async function loadPresentation() {
    const response = await fetch('content/presentation/slides.html?v=v10-cleanup1');
    if (!response.ok) throw new Error('Presentation files are unavailable.');
    page.innerHTML = await response.text();

    const slides = [...page.querySelectorAll('.deck-slide')];
    const navigation = page.querySelector('.deck-navigation');
    const header = document.querySelector('.topbar');
    trackReadingPosition({
      page,
      navigation,
      content: page.querySelector('.deck-slides'),
      links: createContents(slides, navigation),
      sectionFor: button => document.getElementById(button.getAttribute('aria-controls')),
      readingLine: () => {
        const headerHeight = header.getBoundingClientRect().height;
        return headerHeight + Math.max(24, (window.innerHeight - headerHeight) * 0.25);
      },
    });
  }

  function initialize() {
    if (location.hash !== '#presentation' || loading) return;
    loading = loadPresentation().catch(error => {
      page.textContent = 'Unable to load presentation: ' + error.message;
      loading = null;
    });
  }

  window.addEventListener('hashchange', initialize);
  initialize();
})();
