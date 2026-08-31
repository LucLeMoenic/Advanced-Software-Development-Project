<template>
  <main class="home">
    <p class="eyebrow">Advanced Software Development</p>
    <h1>Project Home</h1>
    <p class="intro">Open a team feature from the integrated application.</p>

    <nav aria-label="Project features">
      <ul class="feature-list">
        <li>
          <a class="feature-link" href="/accommodation/">
            <strong>Accommodation Recommender</strong>
            <span>Search, rank, and manage saved accommodation searches.</span>
          </a>
        </li>
        <li><a class="student-link" href="http://localhost:5102">Student 2</a></li>
        <li><a class="student-link" href="http://localhost:5103">Student 3</a></li>
        <li><a class="student-link" href="http://localhost:5104">Student 4</a></li>
        <li><a class="student-link" href="http://localhost:5105">Student 5</a></li>
      </ul>
    </nav>
  </main>
</template>

<style>
.home {
  width: min(52rem, calc(100% - 2rem));
  margin: 0 auto;
  padding: 4rem 0;
}

.eyebrow {
  margin: 0;
  color: #476582;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0.5rem 0;
  color: #2c3e50;
  font-size: clamp(2rem, 6vw, 3.5rem);
}

.intro {
  margin: 0 0 2rem;
  color: #52606d;
  font-size: 1.1rem;
}

.feature-list {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.feature-link,
.student-link {
  display: block;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  color: #1f2933;
  text-decoration: none;
}

.feature-link {
  padding: 1.25rem;
  background: #f8fafc;
}

.feature-link strong,
.feature-link span {
  display: block;
}

.feature-link span {
  margin-top: 0.35rem;
  color: #52606d;
}

.student-link {
  padding: 0.85rem 1rem;
}

.feature-link:hover,
.student-link:hover {
  border-color: #476582;
  background: #eef4f8;
}

.feature-link:focus-visible,
.student-link:focus-visible {
  outline: 3px solid #2563eb;
  outline-offset: 3px;
}
</style>
