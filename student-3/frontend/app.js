/*
 * The backend endpoints return JSON, not HTML fragments, so the browse
 * buttons/form below use hx-swap="none" (stop htmx from injecting raw JSON
 * into the page) and hx-on::after-request to hand the response to these
 * handlers, which render it and then call htmx.process() so any new
 * hx-* attributes in the freshly-inserted markup (e.g. the itinerary
 * button) get wired up too.
 */

/**
 * Attraction names/descriptions come from the CRUD API (any client can POST
 * one) and recommendation text comes from the LLM, so both are untrusted by
 * the time they reach the DOM. Always pass user- or model-supplied text
 * through this before interpolating it into innerHTML.
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
 * `attraction` has: id, name, category, description, rating.
 *
 * Rating is shown only when present (seed data always has one, but
 * user-created attractions via the API may omit it) so a missing rating
 * doesn't render as a literal "null" badge. Descriptions aren't truncated -
 * Release 0's seeded copy is already short, and clipping risks cutting a
 * sentence mid-word for longer user-submitted ones.
 *
 * name/description/category come from the CRUD API, so they're untrusted
 * and go through escapeHtml() before hitting innerHTML. The "Add to
 * itinerary" button's hx-vals payload is limited to the numeric id for the
 * same reason - never interpolate free-text fields into an HTML attribute.
 */
function attractionCardHtml(attraction) {
  const ratingBadge = attraction.rating != null
    ? `<span class="rating">★ ${escapeHtml(attraction.rating)}</span>`
    : '';

  return `
    <article class="card">
      <h3>${escapeHtml(attraction.name)}</h3>
      <p class="category">${escapeHtml(attraction.category)}</p>
      ${ratingBadge}
      <p class="description">${escapeHtml(attraction.description)}</p>
      <button type="button"
              hx-post="/api/itinerary"
              hx-vals='{"attraction_id": ${attraction.id}}'
              hx-swap="none"
              hx-on::after-request="this.textContent = 'Added'; this.disabled = true;">
        Add to itinerary
      </button>
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

function renderRecommendation(event) {
  const box = document.getElementById('recommend-result');
  const data = parseJsonResponse(event);

  if (event.detail.xhr.status >= 400 || data === null) {
    const message = (data && data.message) || 'Something went wrong, please try again.';
    box.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    return;
  }

  const sourceLabel = {
    ai: 'AI',
    ai_retry: 'AI (retried)',
    fallback: 'Templated fallback',
  }[data.source] || data.source;

  box.innerHTML = `
    <p class="rec-source">Source: ${escapeHtml(sourceLabel)}</p>
    <p class="rec-text">${escapeHtml(data.recommendation).replace(/\n/g, '<br>')}</p>
  `;
}
