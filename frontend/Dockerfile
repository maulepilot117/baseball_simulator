# Multi-stage build for React/Deno frontend
FROM denoland/deno:latest AS base

# Set working directory
WORKDIR /app

# Development stage
FROM base AS development

# Install Node.js for compatibility with some packages
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and set permissions first
RUN useradd -m -u 1000 frontenduser && \
    mkdir -p /home/frontenduser/.cache/deno && \
    chown -R frontenduser:frontenduser /app /home/frontenduser/.cache && \
    chown -R frontenduser:frontenduser /deno-dir

# Set Deno cache directory
ENV DENO_DIR=/home/frontenduser/.cache/deno

USER frontenduser

# Copy package files first to cache dependencies
COPY --chown=frontenduser:frontenduser deno.json deps.ts ./

# Cache dependencies as non-root user
RUN deno cache --reload deps.ts

# Copy source code
COPY --chown=frontenduser:frontenduser . .

# Expose port
EXPOSE 3000

# Health check for development (simplified)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Run the development server
CMD ["deno", "task", "dev"]

# Default to development stage
FROM development