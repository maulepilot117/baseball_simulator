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

# Copy package files first to cache dependencies
COPY deno.json deps.ts ./

# Cache dependencies
RUN deno cache --reload deps.ts

# Copy source code
COPY . .

# Create non-root user and set permissions
RUN useradd -m -u 1000 frontenduser && chown -R frontenduser:frontenduser /app
USER frontenduser

# Expose port
EXPOSE 3000

# Health check for development (simplified)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Run the development server
CMD ["deno", "task", "dev"]

# Build stage
FROM base AS builder

# Install Node.js for build tools
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy package files and dependencies
COPY deno.json deps.ts ./

# Cache dependencies
RUN deno cache --reload deps.ts

# Copy source code
COPY . .

# Build the application
RUN deno task build

# Production stage
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built app from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Note: nginx user already exists in nginx:alpine

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]