# Summary tab maintenance

The Summary tab (`#presentation`) displays all ten slides from the interview v10 deck in
one vertical document. Scroll down to read in order, or use the desktop contents
sidebar to scroll to a slide.

## Files and responsibilities

- `content/presentation/slides.html` owns the slide order, titles, accessible
  descriptions and contents groups. A `data-group` attribute starts a new group;
  no slide indices need to be maintained in JavaScript.
- `content/presentation/v10/` contains the verified 1920-by-1080 slide exports
  and a manifest recording the source deck and image checksums.
- `assets/presentation.js` loads the slide document once and creates its contents.
- `assets/reading-position.js` tracks reading position for both the presentation
  and notebook readers. Each reader supplies its targets and sticky-header offset.
- `assets/presentation.css` controls the layout.

The slide images preserve the user's PowerPoint layout and 16:9 proportions.
They scale to the available width without a fixed minimum canvas width. Below
901px, the sidebar is hidden to leave room for the slides. The slides retain
white backgrounds in both site themes. Speaker notes are not included.

## Updating the deck

The editable source is `Coffee_Shop_Demand_Forecasting_Interview_v10.pptx` in the
sibling `Coffee Shop Interview/output` folder. The workflow and recursive
forecasting draw.io sources are also in that folder.

When the deck changes, export and inspect the affected slides, update their
images and accessible descriptions, then refresh the manifest checksums and
cache versions in the HTML and loader. The presentation uses those exports
directly; it has no separate model-results or diagram-generation pipeline.

The current order is cover, Business Overview, Project Workflow, Demand
Preparation, Evaluation Design, Statistical Methods, Machine Learning Methods,
May Model Selection, June Forecast Performance and July Planning Outlook.

For a local preview, serve `docs` on the loopback interface and open
`http://127.0.0.1:8000/#presentation`.
