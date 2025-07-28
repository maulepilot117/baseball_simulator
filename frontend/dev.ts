#!/usr/bin/env deno run --allow-net --allow-read --allow-write --allow-env

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { serveDir } from "https://deno.land/std@0.208.0/http/file_server.ts";

const port = parseInt(Deno.env.get("PORT") || "3000");

console.log(`🚀 Starting development server on http://localhost:${port}`);

await serve(async (req) => {
  const pathname = new URL(req.url).pathname;
  
  // Handle TypeScript files - transpile on-the-fly for browser
  if (pathname.endsWith('.tsx') || pathname.endsWith('.ts')) {
    try {
      const filePath = pathname.startsWith('/') ? pathname.slice(1) : pathname;
      
      // Check if file exists
      try {
        const fileInfo = await Deno.stat(filePath);
        if (fileInfo.isFile) {
          console.log(`Transpiling TypeScript on-the-fly: ${pathname}`);
          
          // Use dynamic import to let Deno handle the TypeScript compilation
          const moduleUrl = new URL(filePath, `file://${Deno.cwd()}/`).href;
          
          try {
            // This will cause Deno to compile the TypeScript and cache it
            await import(moduleUrl);
            
            // Read the TypeScript source and perform basic transformation for browser
            const tsContent = await Deno.readTextFile(filePath);
            
            // Simple transformation to make it browser-compatible
            let jsContent = tsContent
              // Transform JSX imports to use React 18 automatic runtime
              .replace(/^import React from ['"]react['"];?\s*$/gm, '')
              .replace(/^import \* as React from ['"]react['"];?\s*$/gm, '')
              // Keep other imports as-is since we have importmap
              ;
            
            return new Response(jsContent, {
              headers: { 
                "content-type": "application/javascript; charset=utf-8",
                "cache-control": "no-cache"
              },
            });
          } catch (importError) {
            console.error(`Error importing ${filePath}:`, importError);
            return new Response(`// Error compiling ${pathname}: ${importError.message}`, {
              status: 500,
              headers: { 
                "content-type": "application/javascript; charset=utf-8",
                "cache-control": "no-cache"
              },
            });
          }
        }
      } catch {
        return new Response(`// TypeScript file not found: ${pathname}`, {
          status: 404,
          headers: { 
            "content-type": "application/javascript; charset=utf-8",
            "cache-control": "no-cache"
          },
        });
      }
    } catch (error) {
      console.error(`Error serving ${pathname}:`, error);
      return new Response(`// Error serving ${pathname}: ${error.message}`, {
        status: 500,
        headers: { "content-type": "application/javascript; charset=utf-8" },
      });
    }
  }
  
  // Handle CSS files with proper MIME type  
  if (pathname.endsWith('.css')) {
    try {
      const filePath = pathname.startsWith('/') ? pathname.slice(1) : pathname;
      const fileContent = await Deno.readTextFile(filePath);
      return new Response(fileContent, {
        headers: { 
          "content-type": "text/css; charset=utf-8",
          "cache-control": "no-cache"
        },
      });
    } catch (error) {
      return new Response(`/* Error loading ${pathname}: ${error.message} */`, {
        status: 404,
        headers: { "content-type": "text/css; charset=utf-8" },
      });
    }
  }
  
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
    <script type="importmap">
    {
      "imports": {
        "react": "https://esm.sh/react@18.2.0",
        "react-dom": "https://esm.sh/react-dom@18.2.0",
        "react-dom/client": "https://esm.sh/react-dom@18.2.0/client",
        "react-router-dom": "https://esm.sh/react-router-dom@6.8.1",
        "recharts": "https://esm.sh/recharts@2.12.7",
        "lucide-react": "https://esm.sh/lucide-react@0.263.1"
      }
    }
    </script>
</head>
<body>
    <div id="root">
        <div style="padding: 20px; background: #f0f0f0; border: 1px solid #ccc;">
            <h1>Baseball Simulation</h1>
            <p>Loading JavaScript modules...</p>
            <div id="status">Initializing...</div>
        </div>
    </div>
    <script type="module">
        console.log("Inline script starting...");
        document.getElementById("status").textContent = "Script loaded successfully";
        
        // Try to load the main module
        try {
            import('/src/main.tsx').then(() => {
                console.log("Main module loaded");
                const statusEl = document.getElementById("status");
                if (statusEl) statusEl.textContent = "Main module loaded";
            }).catch(error => {
                console.error("Failed to load main module:", error);
                const statusEl = document.getElementById("status");
                if (statusEl) statusEl.innerHTML = '<span style="color: red;">Failed to load main module: ' + error.message + '</span>';
            });
        } catch (error) {
            console.error("Import error:", error);
            const statusEl = document.getElementById("status");
            if (statusEl) statusEl.innerHTML = '<span style="color: red;">Import error: ' + error.message + '</span>';
        }
    </script>
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