import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 3000, // Read PORT env variable or use 5173 as fallback
    host: "0.0.0.0" // Allow external access
  }
});
