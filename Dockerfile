# frontend
FROM node:20-bullseye AS frontend-builder
# Set working directory
WORKDIR /app/frontend
# Copy package.json and package-lock.json (if exists)
COPY ./frontend/package*.json ./
RUN npm ci
COPY ./frontend/ .
RUN npm run build


# Stage 2: Create the final Python container
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"


# Copy the built React frontend into FastAPI static files directory
COPY --from=frontend-builder /app/frontend/dist /app/static

EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "200"]
