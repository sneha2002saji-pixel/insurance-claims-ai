FROM node:20-alpine AS base

# ── deps stage ────────────────────────────────────────────────────────────────
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy workspace manifests so npm ci can resolve the shared-types workspace
COPY package.json package-lock.json ./
COPY packages/shared-types/package.json ./packages/shared-types/
COPY apps/web/package.json ./apps/web/

RUN npm ci

# ── builder stage ─────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules

# Copy source
COPY packages/shared-types/ ./packages/shared-types/
COPY apps/web/ ./apps/web/

WORKDIR /app/apps/web

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── runner stage ──────────────────────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# In a monorepo standalone build, Next.js mirrors the workspace path inside the
# standalone output: the entry point is apps/web/server.js, not server.js.
WORKDIR /app/apps/web

CMD ["node", "server.js"]
