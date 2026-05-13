import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue()],
  clearScreen: false,
  server: {
    strictPort: true,
    port: 1420,
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: "es2022",
    minify: "esbuild",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("@tauri-apps")) return "vendor-tauri";
          if (id.includes("@element-plus/icons-vue")) return "vendor-element-icons";
          if (id.includes("element-plus")) {
            const match = id.match(/element-plus[/\\]es[/\\]components[/\\]([^/\\]+)/);
            return match ? `element-${match[1]}` : "vendor-element-plus";
          }
          if (id.includes("@vue") || id.includes("vue")) return "vendor-vue";
          return "vendor";
        },
      },
    },
  },
});
