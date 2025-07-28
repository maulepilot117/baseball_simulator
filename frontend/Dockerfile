# Multi-stage build for React frontend with Vite
FROM node:22-alpine as base

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install --only=production && npm cache clean --force

# Development stage
FROM base as development
RUN npm install && npm cache clean --force
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage  
FROM base as builder
RUN npm install && npm cache clean --force
COPY . .
RUN npm run build

# Production stage with nginx
FROM nginx:alpine as production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

# Create non-root user for security
RUN addgroup -g 1001 -S frontenduser && \
    adduser -S frontenduser -u 1001 -G frontenduser && \
    chown -R frontenduser:frontenduser /usr/share/nginx/html && \
    chown -R frontenduser:frontenduser /var/cache/nginx && \
    chown -R frontenduser:frontenduser /var/log/nginx && \
    chown -R frontenduser:frontenduser /etc/nginx/conf.d

RUN touch /var/run/nginx.pid && \
    chown -R frontenduser:frontenduser /var/run/nginx.pid

USER frontenduser
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]