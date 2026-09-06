<template>
  <main class="page-shell">
    <header class="hero">
      <p class="product-label">Advanced Software Development</p>
      <h1>Agentic AI Trip Planning & Travel Management Platform</h1>
      <p class="hero-copy">
        Choose a team feature from the shared workspace.
      </p>
    </header>

    <section class="features-section" aria-labelledby="features-heading">
      <div class="section-heading">
        <div>
          <h2 id="features-heading">Features</h2>
          <p>Each feature opens in its own service.</p>
        </div>
      </div>

      <nav aria-label="Project features">
        <ul class="feature-grid">
          <li class="featured-item">
            <a class="feature-card feature-card-primary" href="/accommodation/">
              <span class="student-label">Student 1</span>
              <span class="feature-content">
                <strong>Accommodation Recommender</strong>
                <span class="feature-description">
                  Search, rank, and manage saved accommodation recommendations.
                </span>
              </span>
              <span class="feature-action">Open</span>
            </a>
          </li>
          <li>
            <a class="feature-card" href="/itinerary/">
              <span class="student-label">Student 2</span>
              <span class="feature-content">
                <strong>Itinerary Planner</strong>
                <span class="feature-description">
                  Generate and refine a day-by-day journey with AI assistance.
                </span>
              </span>
              <span class="feature-action">Open</span>
            </a>
          </li>
          <li>
            <a class="feature-card" href="http://localhost:5103">
              <span class="student-label">Student 3</span>
              <span class="feature-content">
                <strong>Local Attraction Recommender</strong>
                <span class="feature-description">Browse, review, and manage local attractions, with an AI-suggested pick based on your interests.</span>
              </span>
              <span class="feature-action">Open</span>
            </a>
          </li>
          <li>
            <a class="feature-card" href="/budget/">
              <span class="student-label">Student 4</span>
              <span class="feature-content">
                <strong>Budget &amp; Expense Tracker</strong>
                <span class="feature-description">Compare planned category limits with actual spending.</span>
              </span>
              <span class="feature-action">Open</span>
            </a>
          </li>
          <li>
            <a class="feature-card" href="http://localhost:5105">
              <span class="student-label">Student 5</span>
              <span class="feature-content">
                <strong>Travel Logistics &amp; Advisory</strong>
                <span class="feature-description">Check weather, visa requirements, and transit, then generate AI packing advice.</span>
              </span>
              <span class="feature-action">Open</span>
            </a>
          </li>
        </ul>
      </nav>
    </section>
    <footer class="page-footer">
      Integrated services run together through Docker Compose.
    </footer>
  </main>
</template>
