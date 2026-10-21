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
                hx-post="/attractions-api/itinerary"
                hx-vals='{"attraction_id": ${attraction.id}}'
                hx-swap="none"
                hx-on::after-request="this.textContent = 'Added'; this.disabled = true;">
          Add to itinerary
        </button>
        <button type="button" hx-on:click="showEditForm(${attraction.id})">Edit</button>
        <button type="button"
                class="danger"
                hx-delete="/attractions-api/attractions/${attraction.id}"
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
          hx-put="/attractions-api/attractions/${id}"
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
          hx-post="/attractions-api/reviews"
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
    ? `/attractions-api/attractions?category=${encodeURIComponent(currentCategory)}`
    : '/attractions-api/attractions';

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

/**
 * The backend's Plan -> Act -> Observe -> Adapt loop calls Ollama
 * synchronously and can take anywhere from a couple of seconds (warm
 * model) to most of OLLAMA_TIMEOUT's 120s (cold model, or a retry that
 * doubles the call count) - observed directly in student3-backend's logs.
 * Without this, the form gives no feedback for that whole window, which
 * reads as broken rather than slow: nothing changes on screen and a
 * user has no reason not to click "Get Recommendation" again.
 */
function handleRecommendStart(form) {
  document.getElementById('recommend-result').innerHTML =
    '<p class="loading">Thinking of a recommendation... this can take up to a minute.</p>';
  const button = form.querySelector('button[type="submit"]');
  if (button) button.disabled = true;
}

/**
 * Minimal client-side argument schema for the two Student 3 MCP tools.
 * The backend's GET /api/mcp/tools only returns tool names (Stage 2 scope),
 * so this is what drives the dynamic argument form once a tool is picked.
 * A tool name outside this map (there shouldn't be one, since the backend's
 * own allow list matches exactly these two) falls back to a plain message
 * instead of a broken form - see renderMcpArgs.
 */
const MCP_TOOL_SCHEMAS = {
  'attractions.search': [
    { name: 'category', label: 'Category', type: 'select', options: ['', 'sight', 'restaurant', 'activity'] },
    { name: 'min_rating', label: 'Minimum rating', type: 'number', min: 0, max: 5, step: 0.5 },
    { name: 'limit', label: 'Limit (max 10)', type: 'number', min: 1, max: 10, value: 5 },
  ],
  'attractions.get_reviews': [
    { name: 'attraction_id', label: 'Attraction ID', type: 'number', min: 1, required: true },
  ],
};

function mcpArgFieldHtml(field) {
  const id = `mcp-arg-${field.name}`;
  const label = `<label for="${id}">${escapeHtml(field.label)}</label>`;

  if (field.type === 'select') {
    const options = field.options
      .map((value) => `<option value="${escapeHtml(value)}">${value ? escapeHtml(value) : 'Any'}</option>`)
      .join('');
    return `${label}<select id="${id}" data-arg="${field.name}">${options}</select>`;
  }

  const attrs = [
    field.min != null ? `min="${field.min}"` : '',
    field.max != null ? `max="${field.max}"` : '',
    field.step != null ? `step="${field.step}"` : '',
    field.value != null ? `value="${field.value}"` : '',
    field.required ? 'required' : '',
  ].filter(Boolean).join(' ');
  return `${label}<input id="${id}" type="number" data-arg="${field.name}" ${attrs}>`;
}

function renderMcpArgs(toolName) {
  const container = document.getElementById('mcp-args');
  const schema = MCP_TOOL_SCHEMAS[toolName];
  if (!schema) {
    container.innerHTML = '<p class="empty">No input form available for this tool.</p>';
    return;
  }
  container.innerHTML = schema.map(mcpArgFieldHtml).join('');
}

/** Reads #mcp-args' current inputs into a {tool_arg: value} object, skipping blank optional fields. */
function collectMcpArguments(toolName) {
  const schema = MCP_TOOL_SCHEMAS[toolName] || [];
  const args = {};
  schema.forEach((field) => {
    const input = document.getElementById(`mcp-arg-${field.name}`);
    if (!input || input.value === '') return;
    args[field.name] = field.type === 'select' ? input.value : Number(input.value);
  });
  return args;
}

function setMcpStatus(message, kind) {
  const status = document.getElementById('mcp-status');
  status.innerHTML = message ? `<p class="${kind}">${escapeHtml(message)}</p>` : '';
}

function initMcpPanel() {
  const select = document.getElementById('mcp-tool');
  const runButton = document.getElementById('mcp-run');

  fetch('/attractions-api/mcp/tools')
    .then((response) => response.json().then((data) => ({ status: response.status, data })))
    .then(({ status, data }) => {
      if (status === 503) {
        setMcpStatus('MCP tools are currently disabled.', 'error');
        return;
      }
      if (status !== 200 || !data || !Array.isArray(data.tools)) {
        setMcpStatus('MCP service is offline.', 'error');
        return;
      }
      if (data.tools.length === 0) {
        setMcpStatus('No MCP tools are currently registered.', 'empty');
        return;
      }
      select.innerHTML = data.tools.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
      select.disabled = false;
      runButton.disabled = false;
      renderMcpArgs(select.value);
    })
    .catch(() => setMcpStatus('MCP service is offline.', 'error'));

  select.addEventListener('change', () => renderMcpArgs(select.value));

  document.getElementById('mcp-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const tool = select.value;
    const resultBox = document.getElementById('mcp-result');
    resultBox.innerHTML = '<p class="loading">Running tool...</p>';
    runButton.disabled = true;

    fetch('/attractions-api/mcp/invoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, arguments: collectMcpArguments(tool) }),
    })
      .then((response) => response.json().then((data) => ({ status: response.status, data })))
      .then(({ status, data }) => renderMcpResult(status, data, tool))
      .catch(() => renderMcpResult(502, null, tool))
      .finally(() => { runButton.disabled = false; });
  });
}

function mcpAttractionsSearchResultHtml(result) {
  const rows = result.attractions.map((attraction) => `
    <li>
      <strong>${escapeHtml(attraction.name)}</strong>
      (${escapeHtml(attraction.category)}${attraction.rating != null ? `, ★ ${escapeHtml(attraction.rating)}` : ''})
      <p>${escapeHtml(attraction.description)}</p>
    </li>
  `).join('');
  return `
    <p class="mcp-summary">Showing ${result.attractions.length} of ${result.total_matches} match(es).</p>
    <ul class="mcp-attraction-list">${rows || '<li class="empty">No matches.</li>'}</ul>
  `;
}

function mcpGetReviewsResultHtml(result) {
  const rows = result.reviews.map((review) => `
    <li>${review.rating != null ? `★ ${escapeHtml(review.rating)} — ` : ''}${escapeHtml(review.comment)}</li>
  `).join('');
  return `
    <p class="mcp-summary">Reviews for <strong>${escapeHtml(result.name)}</strong>:</p>
    <ul class="mcp-attraction-list">${rows || '<li class="empty">No reviews yet.</li>'}</ul>
  `;
}

function renderMcpResult(status, data, tool) {
  const box = document.getElementById('mcp-result');

  if (status === 503) {
    box.innerHTML = '<p class="error">MCP tools are currently disabled.</p>';
    return;
  }
  if (status === 502 || data === null) {
    box.innerHTML = '<p class="error">MCP service is offline.</p>';
    return;
  }
  if (status === 400) {
    box.innerHTML = `<p class="error">${escapeHtml((data && data.message) || 'Invalid tool call.')}</p>`;
    return;
  }
  if (tool === 'attractions.search') {
    box.innerHTML = mcpAttractionsSearchResultHtml(data.result);
    return;
  }
  if (tool === 'attractions.get_reviews') {
    box.innerHTML = mcpGetReviewsResultHtml(data.result);
    return;
  }
  box.innerHTML = `<pre>${escapeHtml(JSON.stringify(data.result, null, 2))}</pre>`;
}

document.addEventListener('DOMContentLoaded', initMcpPanel);

/** Matches handleRecommendStart's loading-state pattern for the RAG panel. */
function handleRagStart(form) {
  document.getElementById('rag-result').innerHTML = '<p class="loading">Asking the destination guide...</p>';
  const button = form.querySelector('button[type="submit"]');
  if (button) button.disabled = true;
}

function citationsHtml(citations) {
  if (!citations.length) return '';
  const items = citations.map((citation) => `
    <li>
      <strong>${escapeHtml(citation.source)}</strong>
      (score ${escapeHtml(citation.score)})
      <p>${escapeHtml(citation.snippet)}</p>
    </li>
  `).join('');
  return `<ol class="rag-citations">${items}</ol>`;
}

function renderRagAnswer(event, form) {
  const box = document.getElementById('rag-result');
  const status = event.detail.xhr.status;
  const data = parseJsonResponse(event);
  const button = form.querySelector('button[type="submit"]');
  if (button) button.disabled = false;

  if (status === 503) {
    box.innerHTML = '<p class="error">The destination guide is currently disabled.</p>';
    return;
  }
  if (status === 502 || data === null) {
    box.innerHTML = '<p class="error">The destination guide service is offline.</p>';
    return;
  }
  if (status >= 400) {
    box.innerHTML = `<p class="error">${escapeHtml((data && data.message) || 'Something went wrong, please try again.')}</p>`;
    return;
  }

  const badgeClass = confidenceBadgeClass(data.confidence);

  if (data.confidence === 'insufficient') {
    box.innerHTML = `
      <p class="rag-insufficient">${escapeHtml(data.answer)}</p>
    `;
    return;
  }

  box.innerHTML = `
    <p><span class="confidence-badge ${badgeClass}">${escapeHtml(data.confidence)} confidence</span></p>
    <p class="rag-answer">${escapeHtml(data.answer)}</p>
    ${citationsHtml(data.citations)}
  `;
}

function renderRecommendation(event, form) {
  const box = document.getElementById('recommend-result');
  const data = parseJsonResponse(event);
  const button = form.querySelector('button[type="submit"]');
  if (button) button.disabled = false;

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

/* ==========================================================================
 * Release 2: "Plan a Day with Agents" - the shared Multi-Agent Server.
 *
 * Flow: this page -> /attractions-api/agents/* (Student 3 backend) -> Multi-Agent
 * Server -> Planner -> Worker -> Reviewer -> human review (this page) -> response.
 * The backend chooses the evidence (the catalogue); the workflow runs in the
 * background, so this page polls instead of holding one long request open.
 * ========================================================================== */

/**
 * escapeHtml (above) leaves quotes alone, which is fine between tags but not inside an HTML
 * attribute value. Use this for anything interpolated into an attribute.
 */
function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const AGENT_API = '/attractions-api/agents';
const AGENT_POLL_MS = 3000;
const AGENT_SESSION_KEY = 'student3-agent-workflow';
const AGENT_STAGES = [
  { role: 'Planner', blurb: 'Drafts the plan and names the evidence it needs' },
  { role: 'Worker', blurb: 'Carries out the plan using only catalogue facts' },
  { role: 'Reviewer', blurb: 'Checks the work against the evidence' },
  { role: 'You', blurb: 'Approve, correct, accept part of it, or reject' },
];
const AGENT_RUNNING_STAGE = { queued: 0, planning: 0, working: 1, reviewing: 2, awaiting_human_review: 3 };
const AGENT_STAGE_BY_NAME = { planning: 0, working: 1, reviewing: 2 };
const AGENT_DECIDED_LABEL = {
  approved: 'Approved',
  corrected: 'Corrected by you',
  partially_accepted: 'Partially accepted',
  rejected: 'Rejected',
};

let agentRecord = null;
let agentPollTimer = null;
let agentClockTimer = null;
let agentStartedAt = 0;
let agentPollFailures = 0;

function agentStore(action, value) {
  // sessionStorage can throw (private windows, blocked storage); the page works without it.
  try {
    if (action === 'set') sessionStorage.setItem(AGENT_SESSION_KEY, value);
    else if (action === 'clear') sessionStorage.removeItem(AGENT_SESSION_KEY);
    else return sessionStorage.getItem(AGENT_SESSION_KEY);
  } catch (err) {
    return null;
  }
  return null;
}

function setAgentStatus(message, kind) {
  const status = document.getElementById('agent-status');
  status.innerHTML = message ? `<p class="${kind}">${escapeHtml(message)}</p>` : '';
}

function setAgentFormEnabled(enabled) {
  document.getElementById('agent-task').disabled = !enabled;
  document.getElementById('agent-category').disabled = !enabled;
  document.getElementById('agent-start').disabled = !enabled;
}

function agentFetch(path, options) {
  return fetch(`${AGENT_API}${path}`, options)
    .then((response) => response.json().then((data) => ({ status: response.status, data }))
      .catch(() => ({ status: response.status, data: null })));
}

/** One of: done | active | waiting | failed | degraded | pending, per stage index. */
function agentStageStates(record) {
  const states = AGENT_STAGES.map(() => 'pending');
  if (record.status === 'failed') {
    const failedAt = AGENT_STAGE_BY_NAME[(record.error || {}).stage];
    for (let i = 0; i < states.length; i += 1) {
      if (failedAt === undefined) break;
      if (i < failedAt) states[i] = 'done';
      else if (i === failedAt) states[i] = 'failed';
    }
    return states;
  }
  if (AGENT_DECIDED_LABEL[record.status]) return states.map(() => 'done');
  const current = AGENT_RUNNING_STAGE[record.status] ?? 0;
  for (let i = 0; i < current; i += 1) states[i] = 'done';
  states[current] = current === 3 ? 'waiting' : 'active';
  if (record.review && record.review.degraded) states[2] = 'degraded';
  return states;
}

function agentStageLabel(state, index) {
  if (state === 'done') return 'Done';
  if (state === 'waiting') return 'Waiting for you';
  if (state === 'failed') return 'Failed';
  if (state === 'degraded') return 'Automatic checks only';
  if (state === 'active') {
    const seconds = Math.max(0, Math.floor((Date.now() - agentStartedAt) / 1000));
    return index === 3 ? 'Waiting for you' : `Working... ${seconds}s in total`;
  }
  return 'Pending';
}

function renderAgentStages(record) {
  const list = document.getElementById('agent-stages');
  const states = agentStageStates(record);
  list.hidden = false;
  list.innerHTML = AGENT_STAGES.map((stage, index) => `
    <li class="agent-stage is-${states[index]}"${states[index] === 'active' ? ' aria-current="step"' : ''}>
      <span class="agent-stage-role">${escapeHtml(stage.role)}</span>
      <span class="agent-stage-blurb">${escapeHtml(stage.blurb)}</span>
      <span class="agent-stage-state">${escapeHtml(agentStageLabel(states[index], index))}</span>
    </li>
  `).join('');
}

function evidenceChipsHtml(ids) {
  return (ids || []).map((id) => `<span class="evidence-chip">${escapeHtml(id)}</span>`).join(' ');
}

function agentPlanHtml(plan) {
  if (!plan) return '';
  const steps = plan.steps.map((step) => `<li>${escapeHtml(step.description)}</li>`).join('');
  const criteria = plan.success_criteria.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  return `
    <article class="agent-card">
      <h3>Planner: the plan</h3>
      <p>${escapeHtml(plan.objective)}</p>
      <ol class="agent-steps">${steps}</ol>
      <p class="agent-meta">Evidence it asked the Worker to use: ${evidenceChipsHtml(plan.required_evidence_ids)}</p>
      <details><summary>Success criteria</summary><ul>${criteria}</ul></details>
    </article>
  `;
}

function agentWorkHtml(work) {
  if (!work) return '';
  const items = work.items.map((item) => `
    <li class="agent-item">
      <strong>${escapeHtml(item.subject)}</strong>
      <span class="agent-item-id">${escapeHtml(item.id)}</span>
      <p>${escapeHtml(item.detail)}</p>
      <p class="agent-meta">Evidence: ${evidenceChipsHtml(item.evidence_ids)}</p>
    </li>
  `).join('');
  return `
    <article class="agent-card">
      <h3>Worker: the suggestion</h3>
      <p>${escapeHtml(work.summary)}</p>
      <ul class="agent-items">${items}</ul>
    </article>
  `;
}

function agentReviewHtml(review) {
  if (!review) return '';
  const findings = review.findings.length
    ? review.findings.map((finding) => `
        <li class="finding finding-${escapeAttr(finding.severity)}">
          <span class="finding-severity">${escapeHtml(finding.severity)}</span>
          ${finding.item_id ? `<span class="agent-item-id">${escapeHtml(finding.item_id)}</span>` : ''}
          ${escapeHtml(finding.message)}
        </li>`).join('')
    : '<li class="finding">No issues found.</li>';
  const recommendations = review.recommendations.map((text) => `<li>${escapeHtml(text)}</li>`).join('');
  const degraded = review.degraded
    ? '<p class="agent-warning">The Reviewer agent did not produce a valid review, so only the automatic checks ran. Check every item against its evidence yourself.</p>'
    : '';
  return `
    <article class="agent-card">
      <h3>Reviewer: verdict
        <span class="verdict-badge verdict-${escapeAttr(review.verdict)}">${escapeHtml(review.verdict)}</span>
      </h3>
      ${degraded}
      <ul class="agent-findings">${findings}</ul>
      ${recommendations ? `<p class="agent-meta">Recommendations</p><ul>${recommendations}</ul>` : ''}
    </article>
  `;
}

function agentReviewFormHtml(record) {
  const partial = record.work.items.map((item) => `
    <label class="agent-check">
      <input type="checkbox" name="accept" value="${escapeAttr(item.id)}" checked>
      ${escapeHtml(item.subject)} <span class="agent-item-id">${escapeHtml(item.id)}</span>
    </label>`).join('');
  const correct = record.work.items.map((item) => `
    <label for="agent-fix-${escapeAttr(item.id)}">${escapeHtml(item.subject)}
      <span class="agent-item-id">${escapeHtml(item.id)}</span></label>
    <textarea id="agent-fix-${escapeAttr(item.id)}" data-item-id="${escapeAttr(item.id)}" rows="2" maxlength="400">${escapeHtml(item.detail)}</textarea>`).join('');
  return `
    <form id="agent-decision-form" class="agent-card" novalidate>
      <h3>Your decision</h3>
      <fieldset>
        <legend class="visually-hidden">Decision</legend>
        <label class="agent-check"><input type="radio" name="decision" value="approve" checked> Approve as is</label>
        <label class="agent-check"><input type="radio" name="decision" value="correct"> Correct it</label>
        <label class="agent-check"><input type="radio" name="decision" value="partial"> Accept only some items</label>
        <label class="agent-check"><input type="radio" name="decision" value="reject"> Reject</label>
      </fieldset>
      <div data-for="partial" hidden><p class="agent-meta">Items to keep:</p>${partial}</div>
      <div data-for="correct" hidden>
        <label for="agent-fix-summary">Summary</label>
        <textarea id="agent-fix-summary" rows="2" maxlength="400">${escapeHtml(record.work.summary)}</textarea>
        ${correct}
        <p class="agent-meta">Each item keeps its subject and evidence; edit the wording only.</p>
      </div>
      <label for="agent-notes">Notes <span id="agent-notes-hint" class="agent-meta">(required to reject)</span></label>
      <textarea id="agent-notes" rows="2" maxlength="1000"></textarea>
      <p id="agent-decision-error" class="error" role="alert"></p>
      <button type="submit" id="agent-decide">Record decision</button>
    </form>
  `;
}

function agentFinalHtml(record) {
  const decision = record.human_decision || {};
  const items = record.final_output && record.final_output.items.length
    ? `<ul class="agent-items">${record.final_output.items.map((item) => `
        <li class="agent-item"><strong>${escapeHtml(item.subject)}</strong><p>${escapeHtml(item.detail)}</p></li>`).join('')}</ul>`
    : '<p class="empty">Nothing was accepted from this run.</p>';
  return `
    <article class="agent-card agent-final">
      <h3>Final outcome
        <span class="verdict-badge decided-${escapeAttr(record.status)}">${escapeHtml(AGENT_DECIDED_LABEL[record.status])}</span>
      </h3>
      ${record.final_output ? `<p>${escapeHtml(record.final_output.summary)}</p>` : ''}
      ${items}
      ${decision.notes ? `<p class="agent-meta">Your notes: ${escapeHtml(decision.notes)}</p>` : ''}
      <p class="agent-meta">Workflow ${escapeHtml(record.id)}</p>
      <button type="button" id="agent-again">Plan another day</button>
    </article>
  `;
}

function renderAgentResult(record) {
  const box = document.getElementById('agent-result');
  if (record.status === 'failed') {
    const error = record.error || {};
    box.innerHTML = `
      ${agentPlanHtml(record.plan)}${agentWorkHtml(record.work)}
      <p class="error">The agents could not finish (${escapeHtml(error.code || 'unknown')}${error.stage ? ` while ${escapeHtml(error.stage)}` : ''}). ${escapeHtml(error.message || '')}</p>
      <button type="button" id="agent-again">Try again</button>`;
  } else if (record.status === 'awaiting_human_review') {
    box.innerHTML = `${agentPlanHtml(record.plan)}${agentWorkHtml(record.work)}${agentReviewHtml(record.review)}${agentReviewFormHtml(record)}`;
    wireAgentDecisionForm(record);
  } else if (AGENT_DECIDED_LABEL[record.status]) {
    box.innerHTML = `${agentPlanHtml(record.plan)}${agentWorkHtml(record.work)}${agentReviewHtml(record.review)}${agentFinalHtml(record)}`;
  } else {
    box.innerHTML = '';
    return;
  }
  const again = document.getElementById('agent-again');
  if (again) again.addEventListener('click', resetAgentPanel);
}

function stopAgentTimers() {
  window.clearTimeout(agentPollTimer);
  window.clearInterval(agentClockTimer);
  agentPollTimer = null;
  agentClockTimer = null;
}

function resetAgentPanel() {
  stopAgentTimers();
  agentRecord = null;
  agentStore('clear');
  document.getElementById('agent-stages').hidden = true;
  document.getElementById('agent-result').innerHTML = '';
  setAgentFormEnabled(true);
  setAgentStatus('', '');
}

function agentIsFinished(record) {
  return record.status === 'awaiting_human_review' || record.status === 'failed' || Boolean(AGENT_DECIDED_LABEL[record.status]);
}

function applyAgentRecord(record) {
  const wasFinished = agentRecord && agentIsFinished(agentRecord) && agentRecord.status === record.status;
  agentRecord = record;
  renderAgentStages(record);
  if (!agentIsFinished(record)) {
    document.getElementById('agent-result').innerHTML = '';
    return;
  }
  stopAgentTimers();
  if (!wasFinished) renderAgentResult(record);
  if (record.status === 'awaiting_human_review') {
    setAgentStatus('The agents have finished. Review their work and record your decision.', 'success');
  } else if (record.status === 'failed') {
    setAgentStatus('The workflow failed.', 'error');
  } else {
    setAgentStatus('Decision recorded.', 'success');
  }
}

function pollAgentWorkflow(id) {
  agentFetch(`/workflows/${encodeURIComponent(id)}`).then(({ status, data }) => {
    if (status === 200 && data) {
      agentPollFailures = 0;
      applyAgentRecord(data);
      if (!agentIsFinished(data)) agentPollTimer = window.setTimeout(() => pollAgentWorkflow(id), AGENT_POLL_MS);
      return;
    }
    if (status === 404) {
      agentStore('clear');
      setAgentStatus('That workflow no longer exists on the Multi-Agent Server.', 'error');
      setAgentFormEnabled(true);
      return;
    }
    agentPollFailures += 1;
    if (agentPollFailures >= 3) {
      setAgentStatus('Lost contact with the Multi-Agent Server. Your workflow is safe on the server; reload to resume.', 'error');
      return;
    }
    agentPollTimer = window.setTimeout(() => pollAgentWorkflow(id), AGENT_POLL_MS);
  }).catch(() => {
    agentPollFailures += 1;
    if (agentPollFailures < 3) agentPollTimer = window.setTimeout(() => pollAgentWorkflow(id), AGENT_POLL_MS);
    else setAgentStatus('Lost contact with the Multi-Agent Server. Reload to resume.', 'error');
  });
}

function beginAgentPolling(id, startedAt) {
  stopAgentTimers();
  agentStartedAt = startedAt;
  agentPollFailures = 0;
  agentClockTimer = window.setInterval(() => {
    if (agentRecord && !agentIsFinished(agentRecord)) renderAgentStages(agentRecord);
  }, 1000);
  pollAgentWorkflow(id);
}

function agentStartError(status, data) {
  const code = data && data.error;
  if (status === 503 && code === 'busy') return 'Another workflow is running. Try again when it finishes.';
  if (status === 503) return 'Multi-Agent is currently disabled.';
  if (status === 502) return 'The Multi-Agent Server is offline.';
  return (data && data.message) || 'Something went wrong, please try again.';
}

function handleAgentStart(event) {
  event.preventDefault();
  const task = document.getElementById('agent-task').value.trim();
  const category = document.getElementById('agent-category').value;
  if (task.length < 3) {
    setAgentStatus('Describe what the plan is for (at least 3 characters).', 'error');
    return;
  }
  setAgentFormEnabled(false);
  document.getElementById('agent-result').innerHTML = '';
  setAgentStatus('Starting the agents...', 'loading');

  agentFetch('/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(category ? { task, category } : { task }),
  }).then(({ status, data }) => {
    if (status !== 202 || !data || !data.id) {
      setAgentStatus(agentStartError(status, data), 'error');
      setAgentFormEnabled(true);
      return;
    }
    agentStore('set', data.id);
    setAgentStatus(`The agents are working from ${data.evidence_count} catalogue entries. This usually takes one to two minutes.`, 'loading');
    applyAgentRecord({ id: data.id, status: data.status, review: null, error: null });
    beginAgentPolling(data.id, Date.now());
  }).catch(() => {
    setAgentStatus('The Multi-Agent Server is offline.', 'error');
    setAgentFormEnabled(true);
  });
}

function wireAgentDecisionForm(record) {
  const form = document.getElementById('agent-decision-form');
  const sections = form.querySelectorAll('[data-for]');
  const sync = () => {
    const chosen = form.elements.decision.value;
    sections.forEach((section) => { section.hidden = section.dataset.for !== chosen; });
  };
  form.addEventListener('change', sync);
  sync();
  form.addEventListener('submit', (event) => submitAgentDecision(event, record));
}

/** Build the request body for the chosen decision, or return {error} (mirrors the server's rules). */
function collectAgentDecision(form, record) {
  const decision = form.elements.decision.value;
  const notes = document.getElementById('agent-notes').value.trim();
  const body = { decision, notes };
  if (decision === 'reject' && !notes) return { error: 'Please say why you are rejecting this.' };
  if (decision === 'partial') {
    body.accepted_item_ids = Array.from(form.querySelectorAll('input[name="accept"]:checked')).map((box) => box.value);
    if (!body.accepted_item_ids.length) return { error: 'Choose at least one item to keep, or reject instead.' };
  }
  if (decision === 'correct') {
    const summary = document.getElementById('agent-fix-summary').value.trim();
    const items = record.work.items.map((item) => ({
      id: item.id,
      subject: item.subject,
      evidence_ids: item.evidence_ids,
      detail: document.getElementById(`agent-fix-${item.id}`).value.trim(),
    }));
    if (!summary || items.some((item) => !item.detail)) return { error: 'The summary and every item need some text.' };
    body.corrected_output = { summary, items };
  }
  return { body };
}

function submitAgentDecision(event, record) {
  event.preventDefault();
  const form = event.target;
  const errorBox = document.getElementById('agent-decision-error');
  const { body, error } = collectAgentDecision(form, record);
  if (error) {
    errorBox.textContent = error;
    return;
  }
  errorBox.textContent = '';
  const button = document.getElementById('agent-decide');
  button.disabled = true;

  agentFetch(`/workflows/${encodeURIComponent(record.id)}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(({ status, data }) => {
    if (status === 200 && data) {
      applyAgentRecord(data);
      renderAgentResult(data);
      return;
    }
    button.disabled = false;
    if (status === 409) errorBox.textContent = 'This workflow already has a decision. Reload to see it.';
    else if (status === 502 || status === 503) errorBox.textContent = 'The Multi-Agent Server is not reachable. Try again.';
    else errorBox.textContent = (data && data.message) || 'Something went wrong, please try again.';
  }).catch(() => {
    button.disabled = false;
    errorBox.textContent = 'The Multi-Agent Server is not reachable. Try again.';
  });
}

function initAgentsPanel() {
  const form = document.getElementById('agent-form');
  if (!form) return;
  form.addEventListener('submit', handleAgentStart);

  agentFetch('/status').then(({ status, data }) => {
    if (status === 503) {
      setAgentStatus('Multi-Agent is currently disabled.', 'error');
      return;
    }
    if (status !== 200 || !data) {
      setAgentStatus('The Multi-Agent Server is offline.', 'error');
      return;
    }
    setAgentFormEnabled(true);
    setAgentStatus(data.busy ? 'The agents are busy with another workflow.' : '', 'loading');
    const saved = agentStore('get');
    if (saved) {
      setAgentFormEnabled(false);
      setAgentStatus('Resuming your workflow...', 'loading');
      beginAgentPolling(saved, Date.now());
    }
  }).catch(() => setAgentStatus('The Multi-Agent Server is offline.', 'error'));
}

document.addEventListener('DOMContentLoaded', initAgentsPanel);

/**
 * When the deployment runs with AI-Mode off (the required cloud baseline), say so up front: the
 * suggestion below then comes from the attraction catalogue alone, never from a model.
 */
function initRecommendStatus() {
  const note = document.getElementById('recommend-status');
  if (!note) return;
  fetch('/attractions-api/capabilities')
    .then((response) => response.json().then((data) => ({ code: response.status, data })))
    .then(({ code, data }) => {
      if (code === 200 && data && data.aiEnabled === false) {
        note.innerHTML = '<p class="empty">AI-Mode is disabled in this deployment. Suggestions come from the attraction catalogue only.</p>';
      }
    })
    .catch(() => {});
}

document.addEventListener('DOMContentLoaded', initRecommendStatus);
