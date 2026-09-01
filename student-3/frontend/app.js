/*
 * The backend endpoints return JSON, not HTML fragments, so the browse
 * buttons/form below use hx-swap="none" (stop htmx from injecting raw JSON
 * into the page) and hx-on::after-request to hand the response to these
 * handlers, which render it and then call htmx.process() so any new
 * hx-* attributes in the freshly-inserted markup (e.g. the itinerary
 * button) get wired up too.
 */

/**
 * Attraction names/descriptions come from the CRUD API, and any client can
 * POST one, so treat them as untrusted by the time they reach the DOM.
 * Always pass this text through here before interpolating it into innerHTML.
 */
function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value ?? '';
  return div.innerHTML;
}

function parseJsonResponse(event) {
  try {
    return JSON.parse(event.detail.xhr.response);
  } catch (err) {
    return null;
  }
}

/**
 * TODO(you): build the markup for a single attraction card.
 *
 * `attraction` has: id, name, category, description, rating.
 * Must return an HTML string wrapped in one element (e.g. <article>).
 *
 * It should include an "Add to itinerary" button wired via HTMX. Keep the
 * hx-vals payload to the numeric id only (never interpolate free-text
 * fields like name/description into an HTML attribute), e.g.:
 *   <button type="button"
 *           hx-post="/api/itinerary"
 *           hx-vals='{"attraction_id": ${attraction.id}}'
 *           hx-swap="none"
 *           hx-on::after-request="this.textContent = 'Added'; this.disabled = true;">
 *     Add to itinerary
 *   </button>
 *
 * Design choices left to you: how to show category/rating (badge? plain
 * text?), whether to truncate long descriptions, empty-rating handling, etc.
 *
 * IMPORTANT: pass name/description/category through escapeHtml() before
 * interpolating them (they come from the CRUD API, so treat them as
 * untrusted) - see escapeHtml() above.
 */
function attractionCardHtml(attraction) {
  return `
    <article class="card">
      <h3>${escapeHtml(attraction.name)}</h3>
    </article>
  `;
}

function renderAttractions(event) {
  const list = document.getElementById('attraction-list');
  const attractions = parseJsonResponse(event);

  if (event.detail.xhr.status >= 400 || attractions === null) {
    list.innerHTML = '<p class="error">Could not load attractions.</p>';
    return;
  }
  if (attractions.length === 0) {
    list.innerHTML = '<p class="empty">No attractions found for this category.</p>';
    return;
  }

  list.innerHTML = attractions.map(attractionCardHtml).join('');
  htmx.process(list);
}
