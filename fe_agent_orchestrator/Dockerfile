# syntax=docker/dockerfile:1.7

# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (better layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Build the app.
#
# `VITE_API_BASE_URL` must be baked at build time — Vite resolves
# `import.meta.env.VITE_*` during the bundle, not at runtime. The
# top-level docker-compose passes `/api/v1` so nginx (next stage)
# proxies same-origin requests through to the api service.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

# SPA-aware nginx config listening on 3000
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
