import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  base: "./",
  plugins: [vue()],
  server: {
    proxy: {
      "/itinerary-api": {
        target: "http://localhost:5202",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/itinerary-api/, "/api"),
      },
    },
  },
});