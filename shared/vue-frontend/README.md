# ASD Vue Frontend (boilerplate)

This is a minimal Vue 3 + Vite frontend scaffold for the project.

Local dev:

```bash
cd shared/vue-frontend
npm install
npm run dev
```

Build and serve with Docker:

```bash
# from project root
docker build -t asd-vue-frontend:latest -f shared/vue-frontend/Dockerfile shared/vue-frontend
docker run -p 5100:80 asd-vue-frontend:latest
```

Notes:
- Uses Vite (port 5173 by default) for development.
- Production build is served by nginx in the Dockerfile.
