import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../src/admin/static/react/green-vita-hero",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "index.html",
      output: {
        entryFileNames: "green-vita-hero.js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "green-vita-hero.[ext]",
      },
    },
  },
});
