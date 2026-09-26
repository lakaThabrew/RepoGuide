# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies first (layer-cache friendly)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build


# ---- Production stage ----
FROM nginx:1.27-alpine AS production

# Copy Nginx configuration with API reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
