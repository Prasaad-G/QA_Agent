# Production Dockerfile for QA AI Agent
FROM python:3.11-slim

# Prevent Python from buffering stdout and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for caching
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY . .

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Expose server port
EXPOSE 8000

# Start production server with dynamic port binding
CMD uvicorn qa_agent.server.app:app --host 0.0.0.0 --port ${PORT:-8000}

