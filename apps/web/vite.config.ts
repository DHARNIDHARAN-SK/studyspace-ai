import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

// https://vitejs.dev/config/
export default defineConfig(() => {
  const rootEnv = path.resolve(__dirname, "../../.env");
  const envDir = fs.existsSync(rootEnv) ? "../.." : ".";

  return {
    envDir,
    envPrefix: ["VITE_", "SUPABASE_"],
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
