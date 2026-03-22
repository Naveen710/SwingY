# ═══════════════════════════════════════════════════════════════
# FRONTEND DOCKERFILE — Next.js (Standalone Build)
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Dependencies ──
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# ── Stage 2: Build ──
FROM node:20-alpine AS builder
WORKDIR /app

# Accept BACKEND_URL at build time for Next.js rewrites
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 3: Production ──
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Render injects PORT env var
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
