import { cp, mkdir } from "node:fs/promises";

await mkdir("dist/vendor", { recursive: true });
await Promise.all([
  cp("index.html", "dist/index.html"),
  cp("style.css", "dist/style.css"),
  cp("app.js", "dist/app.js"),
  cp("node_modules/htmx.org/dist/htmx.min.js", "dist/vendor/htmx.min.js"),
]);