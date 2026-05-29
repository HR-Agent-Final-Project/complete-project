# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — build
#   Installs deps and compiles the React app into a static bundle.
#   REACT_APP_* vars are baked in at build time — pass them as build-args.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# Default: proxied through nginx on the same host (Docker setup).
# Override with --build-arg REACT_APP_API_URL=https://api.yourcompany.com/api
# for deployments where the frontend and API are on different origins.
ARG REACT_APP_API_URL=/api
ARG REACT_APP_FRONTEND_URL=http://localhost
ARG REACT_APP_USE_MOCK=false

ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_FRONTEND_URL=$REACT_APP_FRONTEND_URL \
    REACT_APP_USE_MOCK=$REACT_APP_USE_MOCK

RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — serve
#   Minimal nginx image — only the compiled bundle, no Node, no source.
# ─────────────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1
