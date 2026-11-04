import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/ai-file-inspector":
        process.env.AI_FILE_INSPECTOR_DEV_API || "http://127.0.0.1:8000",
    },
  },
});
