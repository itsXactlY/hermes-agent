# WhatsApp Bridge — Node.js sidecar for hermes-agent
# Build: cd scripts/whatsapp-bridge && podman build -t hermes-whatsapp-bridge:latest .
FROM node:22-alpine

LABEL org.opencontainers.image.description="WhatsApp Bridge for Hermes Agent"
LABEL org.opencontainers.image.source="https://github.com/NousResearch/hermes-agent"

ENV NODE_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/.playwright

RUN apk add --no-cache \
        chromium \
        nss \
        freetype \
        harfbuzz \
        ca-certificates \
        ttf-freefont \
        curl \
    && ln -s /usr/bin/chromium-browser /usr/bin/chromium

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline --omit=dev && npm cache clean --force

COPY . .

# Run as non-root
USER node

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

CMD ["node", "bridge.js"]
