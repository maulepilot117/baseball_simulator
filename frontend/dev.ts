#!/usr/bin/env deno run --allow-net --allow-read --allow-write --allow-env

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { serveDir } from "https://deno.land/std@0.208.0/http/file_server.ts";

const port = parseInt(Deno.env.get("PORT") || "3000");

console.log(`🚀 Starting development server on http://localhost:${port}`);

await serve(async (req) => {
  const pathname = new URL(req.url).pathname;
  
  // Serve the main HTML file for all routes (SPA)
  if (pathname === "/" || !pathname.includes(".")) {
    return new Response(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baseball Simulation</title>
    <style>
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; }
        #root { min-height: 100vh; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
</body>
</html>
    `, {
      headers: { "content-type": "text/html" },
    });
  }
  
  // Serve static files
  return serveDir(req, {
    fsRoot: ".",
    urlRoot: "",
  });
}, { port });