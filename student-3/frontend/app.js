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
 * htmx forms submit as application/x-www-form-urlencoded by default. The
 * create/update attraction and create review endpoints only accept a JSON
 * body (request.get_json(silent=True) returns None, and therefore an empty
 * payload, for a non-JSON content type - see student-3/backend/app.py) -
 * unlike /api/recommend and /api/itinerary, which explicitly fall back to
 * request.form. Rather than pull in htmx's json-enc extension from a new
 * CDN, this defines the same idea inline: any element (or ancestor) with
 * hx-ext="json-body" gets its parameters serialized as JSON instead.
 *
 * "rating" and "attraction_id" are additionally coerced to numbers, since
 * the reviews endpoint does a strict `isinstance(attraction_id, int)` check
 * - a JSON string would fail validation even though the value looks right.
 * Blank optional fields are dropped entirely so the backend sees them as
 * absent (None) rather than an empty string.
 */
htmx.defineExtension('json-body', {
  onEvent: function (name, evt) {
    if (name === 'htmx:configRequest') {
      evt.detail.headers['Content-Type'] = 'application/json';
    }
  },
  encodeParameters: function (xhr, parameters) {
    xhr.overrideMimeType('text/json');
    const body = {};
    for (const key of Object.keys(parameters)) {
      const value = parameters[key];
      if (value === '' || value === null || value === undefined) continue;
      body[key] = (key === 'rating' || key === 'attraction_id') ? Number(value) : value;
    }
    return JSON.stringify(body);
  },
});

// Populated by renderAttractionsData with the attractions from the last
// list render, keyed by id, so showEditForm/cancelEdit can rebuild a card
// from data already on hand instead of re-fetching a single attraction.
let attractionsCache = {};
// The category filter (if any) behind the attraction list currently on
// screen, so a create/update/delete can refresh the same view afterwards.
let currentCategory = null;

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
    <article class="card" id="attraction-${attraction.id}">
      <h3>${escapeHtml(attraction.name)}</h3>
      <p class="category">${escapeHtml(attraction.category)}</p>
      ${ratingBadge}
      <p class="description">${escapeHtml(attraction.description)}</p>
      <div class="card-actions">
        <button type="button"
                hx-post="/api/itinerary"
                hx-vals='{"attraction_id": ${attraction.id}}'
                hx-swap="none"
                hx-on::after-request="this.textContent = 'Added'; this.disabled = true;">
          Add to itinerary
        </button>
        <button type="button" hx-on:click="showEditForm(${attraction.id})">Edit</button>
        <button type="button"
                class="danger"
                hx-delete="/api/attractions/${attraction.id}"
                hx-confirm="Delete this attraction?"
                hx-swap="none"
                hx-on::after-request="handleDeleteAttraction(event, ${attraction.id})">
          Delete
        </button>
      </div>
      <button type="button" class="review-toggle" hx-on:click="toggleReviewForm(${attraction.id})">
        Leave a review
      </button>
      <div class="review-form" id="review-form-${attraction.id}" hidden></div>
    </article>
  `;
}

/**
 * Renders with empty value attributes, then fills them via the .value DOM
 * property once the form is in the document (see showEditForm). Building
 * `value="${escapeHtml(attraction.name)}"` directly into the markup instead
 * would be unsafe: escapeHtml() only escapes what's needed for text content
 * (&, <, >), not double quotes, so a name containing one could break out of
 * the attribute. Assigning .value in JS sidesteps HTML parsing entirely -
 * it's always treated as data, never markup, so no attribute-escaping bug
 * is possible here regardless of what the string contains.
 */
function editFormHtml(id) {
  return `
    <form class="edit-form"
          hx-ext="json-body"
          hx-put="/api/attractions/${id}"
          hx-swap="none"
          hx-on::after-request="handleUpdateAttraction(event, ${id})">
      <label for="edit-name-${id}">Name</label>
      <input id="edit-name-${id}" name="name" type="text" required maxlength="200">

      <label for="edit-category-${id}">Category</label>
      <select id="edit-category-${id}" name="category" required>
        <option value="sight">Sight</option>
        <option value="restaurant">Restaurant</option>
        <option value="activity">Activity</option>
      </select>

      <label for="edit-description-${id}">Description</label>
      <textarea id="edit-description-${id}" name="description" rows="3" maxlength="500"></textarea>

      <label for="edit-rating-${id}">Rating</label>
      <input id="edit-rating-${id}" name="rating" type="number" min="0" max="5" step="0.5">

      <div class="card-actions">
        <button type="submit">Save</button>
        <button type="button" hx-on:click="cancelEdit(${id})">Cancel</button>
      </div>
      <div class="edit-result" id="edit-result-${id}" aria-live="polite"></div>
    </form>
  `;
}

function showEditForm(id) {
  const attraction = attractionsCache[id];
  const card = document.getElementById(`attraction-${id}`);
  if (!attraction || !card) return;

  card.innerHTML = editFormHtml(id);
  htmx.process(card);

  card.querySelector(`#edit-name-${id}`).value = attraction.name ?? '';
  card.querySelector(`#edit-category-${id}`).value = attraction.category ?? '';
  card.querySelector(`#edit-description-${id}`).value = attraction.description ?? '';
  card.querySelector(`#edit-rating-${id}`).value = attraction.rating ?? '';
}

function cancelEdit(id) {
  const attraction = attractionsCache[id];
  const card = document.getElementById(`attraction-${id}`);
  if (!attraction || !card) return;

  card.outerHTML = attractionCardHtml(attraction);
  htmx.process(document.getElementById(`attraction-${id}`));
}

function handleUpdateAttraction(event, id) {
  if (event.detail.xhr.status >= 400) {
    const data = parseJsonResponse(event);
    const message = (data && data.message) || 'Could not save changes, please try again.';
    const result = document.getElementById(`edit-result-${id}`);
    if (result) result.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    return;
  }
  refreshAttractions();
}

function handleDeleteAttraction(event, id) {
  if (event.detail.xhr.status >= 400) {
    const data = parseJsonResponse(event);
    const message = (data && data.message) || 'Could not delete attraction, please try again.';
    const card = document.getElementById(`attraction-${id}`);
    if (card) {
      const errorBox = card.querySelector('.delete-error') || card.appendChild(document.createElement('p'));
      errorBox.className = 'error delete-error';
      errorBox.innerHTML = escapeHtml(message);
    }
    return;
  }
  refreshAttractions();
}

function reviewFormHtml(attractionId) {
  return `
    <form class="review-form-fields"
          hx-ext="json-body"
          hx-post="/api/reviews"
          hx-vals='{"attraction_id": ${attractionId}}'
          hx-swap="none"
          hx-on::after-request="handleCreateReview(event, ${attractionId})">
      <label for="review-rating-${attractionId}">Rating</label>
      <input id="review-rating-${attractionId}" name="rating" type="number" min="0" max="5" step="0.5">

      <label for="review-comment-${attractionId}">Comment</label>
      <textarea id="review-comment-${attractionId}" name="comment" rows="2" maxlength="500"></textarea>

      <button type="submit">Submit review</button>
    </form>
    <div class="review-result" id="review-result-${attractionId}" aria-live="polite"></div>
  `;
}

function toggleReviewForm(attractionId) {
  const container = document.getElementById(`review-form-${attractionId}`);
  if (!container) return;

  if (container.hidden) {
    if (!container.dataset.built) {
      container.innerHTML = reviewFormHtml(attractionId);
      container.dataset.built = 'true';
      htmx.process(container);
    }
    container.hidden = false;
  } else {
    container.hidden = true;
  }
}

function handleCreateReview(event, attractionId) {
  const result = document.getElementById(`review-result-${attractionId}`);
  if (!result) return;

  if (event.detail.xhr.status >= 400) {
    const data = parseJsonResponse(event);
    const message = (data && data.message) || 'Could not add review, please try again.';
    result.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    return;
  }

  const form = document.getElementById(`review-form-${attractionId}`).querySelector('form');
  if (form) form.reset();
  result.innerHTML = '<p class="success">Review added.</p>';
}

function renderAttractions(event) {
  // currentCategory is set by each filter button's own hx-on:click (see
  // index.html), not read back from this completed request: the buttons
  // are plain <button>s outside a <form>, with the category baked into
  // each one's hx-get URL rather than submitted as a named parameter, so
  // event.detail.requestConfig.parameters.category was always undefined -
  // confirmed by filtering to "Restaurants" and deleting a card, which
  // reset the list to "All" instead of staying filtered.
  renderAttractionsData(event.detail.xhr.status, parseJsonResponse(event));
}

function renderAttractionsData(status, attractions) {
  const list = document.getElementById('attraction-list');

  if (status >= 400 || attractions === null) {
    list.innerHTML = '<p class="error">Could not load attractions.</p>';
    return;
  }
  if (attractions.length === 0) {
    list.innerHTML = '<p class="empty">No attractions found for this category.</p>';
    return;
  }

  attractionsCache = {};
  attractions.forEach((attraction) => { attractionsCache[attraction.id] = attraction; });

  list.innerHTML = attractions.map(attractionCardHtml).join('');
  htmx.process(list);
}

/** Re-fetches the currently filtered attraction list after a create, update, or delete. */
function refreshAttractions() {
  const url = currentCategory
    ? `/api/attractions?category=${encodeURIComponent(currentCategory)}`
    : '/api/attractions';

  fetch(url)
    .then((response) => response.json().then((data) => ({ status: response.status, data })))
    .then(({ status, data }) => renderAttractionsData(status, data))
    .catch(() => renderAttractionsData(502, null));
}

function handleCreateAttraction(event) {
  const result = document.getElementById('create-result');

  if (event.detail.xhr.status >= 400) {
    const data = parseJsonResponse(event);
    const message = (data && data.message) || 'Could not add attraction, please try again.';
    result.innerHTML = `<p class="error">${escapeHtml(message)}</p>`;
    return;
  }

  const data = parseJsonResponse(event);
  document.getElementById('create-attraction-form').reset();
  result.innerHTML = `<p class="success">Added "${escapeHtml(data && data.name)}".</p>`;
  refreshAttractions();
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
