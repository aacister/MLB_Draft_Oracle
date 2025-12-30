FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install the EXACT version of @playwright/mcp that will be used
RUN npm install -g @playwright/mcp@0.0.54

# Install Chromium browsers for the specific Playwright version
RUN npx playwright install chromium --with-deps

# Verify the Chrome binary exists and show its location
RUN echo "Verifying Chrome installation:" && \
    find /root/.cache/ms-playwright -name "chrome" -type f -ls && \
    npx playwright --version

# Set environment variables
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Install Python dependencies
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY *.py ./

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]