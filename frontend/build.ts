#!/usr/bin/env deno run --allow-read --allow-write

import { walk } from "https://deno.land/std@0.208.0/fs/walk.ts";
import { parse } from "https://deno.land/std@0.208.0/path/mod.ts";

console.log("🔨 Building TypeScript files...");

// Create dist directory
try {
  await Deno.mkdir("dist", { recursive: true });
} catch {
  // Directory already exists
}

// Find all TypeScript files
for await (const entry of walk("src", { exts: [".ts", ".tsx"] })) {
  if (entry.isFile) {
    const content = await Deno.readTextFile(entry.path);
    const parsed = parse(entry.path);
    
    // Simple but effective TypeScript stripping
    let jsContent = content
      // Remove import type statements
      .replace(/^import\s+type\s+.*$/gm, '')
      
      // Remove interface declarations (multiline)
      .replace(/^export\s+interface\s+\w+\s*\{[\s\S]*?\n\}/gm, '')
      .replace(/^interface\s+\w+\s*\{[\s\S]*?\n\}/gm, '')
      
      // Remove type declarations (multiline)
      .replace(/^export\s+type\s+\w+\s*=[\s\S]*?;/gm, '')
      .replace(/^type\s+\w+\s*=[\s\S]*?;/gm, '')
      
      // Remove union types
      .replace(/^\s*\|\s*\{[\s\S]*?\}/gm, '')
      .replace(/^\s*\|\s*[^;\n]*$/gm, '')
      
      // Remove type annotations from variables
      .replace(/(const|let|var)\s+(\w+)\s*:\s*[A-Za-z_$][\w\[\]|&\s<>]*\s*=/g, '$1 $2 =')
      
      // Remove type annotations from function parameters  
      .replace(/(\w+)\s*:\s*[A-Za-z_$][\w\[\]|&\s<>]*(?=[,\)])/g, '$1')
      
      // Remove type annotations from destructured parameters
      .replace(/(\{[^}]*\})\s*:\s*[A-Za-z_$][\w\[\]|&\s<>]*(?=\s*[,\)])/g, '$1')
      
      // Remove return type annotations
      .replace(/\)\s*:\s*[A-Za-z_$][\w\[\]|&\s<>]*(?=\s*[{=])/g, ')')
      
      // Remove optional property markers
      .replace(/(\w+)\s*\?\s*:/g, '$1:')
      
      // Remove type assertions
      .replace(/\s+as\s+[A-Za-z_$][\w\[\]|&\s<>]*/g, '')
      
      // Remove generic type parameters
      .replace(/<[A-Za-z_$][\w\[\],\s|&]*>/g, '')
      
      // Remove array type syntax
      .replace(/:\s*[A-Za-z_$]\w*\[\]/g, '')
      
      // Remove typeof expressions
      .replace(/:\s*typeof\s+[\w.]+/g, '')
      
      // Clean up extra whitespace
      .replace(/\n\s*\n\s*\n/g, '\n\n');
    
    // Create output path
    const outputPath = entry.path.replace(/\.tsx?$/, '.js').replace('src/', 'dist/');
    const outputDir = parse(outputPath).dir;
    
    // Create output directory
    await Deno.mkdir(outputDir, { recursive: true });
    
    // Write compiled JavaScript
    await Deno.writeTextFile(outputPath, jsContent);
    
    console.log(`✅ ${entry.path} -> ${outputPath}`);
  }
}

console.log("🎉 Build complete!");