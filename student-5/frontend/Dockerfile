# Student 5 - Travel Logistics & Advisory Service: frontend microservice.
#
# Files are copied by name rather than with `COPY . .` so that nothing else in
# the repo -- other students' services, .venv, storage/*.db -- can end up
# published on the web root.

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY index.html /usr/share/nginx/html/index.html
COPY style.css /usr/share/nginx/html/style.css

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
