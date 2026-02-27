# ──────────────────────────────────────────
# Base
# ──────────────────────────────────────────
FROM node:22-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

# ──────────────────────────────────────────
# Dev — hot reload via volume mount
# ──────────────────────────────────────────
FROM base AS dev
COPY package.json pnpm-lock.yaml ./
RUN pnpm install
CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# ──────────────────────────────────────────
# Build
# ──────────────────────────────────────────
FROM base AS build
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# ──────────────────────────────────────────
# Prod — serve with node
# ──────────────────────────────────────────
FROM base AS prod
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --prod --frozen-lockfile
COPY --from=build /app/.output ./.output
CMD ["node", ".output/server/index.mjs"]
