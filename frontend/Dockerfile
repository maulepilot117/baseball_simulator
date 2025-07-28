# Native TypeScript frontend with Deno
FROM denoland/deno:latest AS base

# Set working directory
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 frontenduser && \
    mkdir -p /home/frontenduser/.cache/deno && \
    chown -R frontenduser:frontenduser /app /home/frontenduser/.cache

# Set Deno cache directory
ENV DENO_DIR=/home/frontenduser/.cache/deno

USER frontenduser

# Development stage
FROM base AS development

# Copy dependency files first for better caching
COPY --chown=frontenduser:frontenduser deno.json deps.ts ./

# Pre-cache dependencies
RUN deno cache --reload deps.ts

# Copy source code
COPY --chown=frontenduser:frontenduser . .

# Cache TypeScript files for faster startup
RUN deno cache --reload src/main.tsx src/App.tsx

# Expose port  
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Run the development server with hot reloading
CMD ["deno", "run", "--allow-net", "--allow-read", "--allow-write", "--allow-env", "--watch", "dev.ts"]

# Production stage
FROM base AS production

# Copy dependency files first for better caching
COPY --chown=frontenduser:frontenduser deno.json deps.ts ./

# Pre-cache dependencies
RUN deno cache --reload deps.ts

# Copy source code
COPY --chown=frontenduser:frontenduser . .

# Cache all TypeScript files and their dependencies
RUN find src -name "*.ts" -o -name "*.tsx" | xargs deno cache --reload

# Expose port
EXPOSE 3000

# Production health check (more frequent)
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Set production environment
ENV NODE_ENV=production
ENV PORT=3000

# Run the server without watch mode for production
CMD ["deno", "run", "--allow-net", "--allow-read", "--allow-write", "--allow-env", "dev.ts"]