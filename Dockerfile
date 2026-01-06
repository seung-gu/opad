# Build stage: Install Python packages
FROM node:20-slim AS builder

# Install Python, pip (no build tools needed - wheels are available)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (matching pyproject.toml)
# All packages have pre-compiled wheels, so no build tools needed
RUN pip3 install --no-cache-dir --break-system-packages \
    crewai[tools]==1.7.2 \
    boto3 \
    python-dotenv

# Install Node.js dependencies and build Next.js
WORKDIR /app
COPY . /app
WORKDIR /app/web
RUN npm install && npm run build

# Runtime stage: Remove build dependencies
FROM node:20-slim

# Install only Python runtime (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy everything from builder
WORKDIR /app
COPY --from=builder /app /app

# Expose port (Railway will set PORT env var)
EXPOSE 3000

# Start Next.js server on Railway's PORT
# Railway sets PORT environment variable, Next.js needs -p flag
WORKDIR /app/web

# Create startup script that exports env vars
RUN echo '#!/bin/sh\n\
export R2_BUCKET_NAME="${R2_BUCKET_NAME}"\n\
export R2_ACCOUNT_ID="${R2_ACCOUNT_ID}"\n\
export R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}"\n\
export R2_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}"\n\
export OPENAI_API_KEY="${OPENAI_API_KEY}"\n\
export SERPER_API_KEY="${SERPER_API_KEY}"\n\
exec npx next start -p ${PORT:-3000}\n' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]

