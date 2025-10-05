# Fresh Frontend Dockerfile
FROM denoland/deno:2.1.4

# Set working directory
WORKDIR /app

# Copy dependency files
COPY deno.json .
COPY deno.lock* .

# Cache dependencies
RUN deno cache --reload deno.json

# Copy application files
COPY . .

# Generate Fresh manifest
RUN deno task manifest

# Build for production
RUN deno task build

# Expose port
EXPOSE 8000

# Start the application
CMD ["deno", "task", "start"]
