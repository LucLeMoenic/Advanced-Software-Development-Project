# Student 5 - Travel Logistics & Advisory Service: frontend microservice.
#
# build context = repo root
#
# The context is the repository root, not this directory, because the image has
# to carry two things that live in different trees: this service's own page,
# and shared/style.css, the team-wide stylesheet the page loads first. Docker
# cannot COPY from outside the build context, so the context is widened rather
# than the shared sheet being duplicated here and left to rot.
#
# Build from the repo root:
#   docker build -f student-5/frontend/Dockerfile -t student5-frontend .
#
# Compose must therefore set `context: .` with
# `dockerfile: student-5/frontend/Dockerfile`.
#
# Files are copied by name rather than with `COPY . .` so that nothing else in
# the repo -- other students' services, .venv, storage/*.db -- can end up
# published on the web root.

FROM nginx:alpine

COPY student-5/frontend/nginx.conf /etc/nginx/conf.d/default.conf

COPY student-5/frontend/index.html /usr/share/nginx/html/index.html
COPY student-5/frontend/style.css /usr/share/nginx/html/style.css

# Team theme, served at /shared/style.css.
COPY shared/style.css /usr/share/nginx/html/shared/style.css

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
