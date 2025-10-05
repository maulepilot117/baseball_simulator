import { defineConfig } from "$fresh/server.ts";

export default defineConfig({
  server: {
    port: 8000,
    hostname: "0.0.0.0",
  },
});
