# Stage 1: Build Frontend (suhani-dashboard-ui)
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY . .
WORKDIR /app/suhani-dashboard-ui
RUN npm install
RUN npm run build


# Stage 2: Final Python Application Image
FROM python:3.11-slim
WORKDIR /app

# Install build dependencies and ffmpeg for audio transcription
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy built frontend assets from node stage
COPY --from=frontend-builder /app/suhani-dashboard-ui/dist /app/suhani-dashboard-ui/dist

EXPOSE 8000

CMD ["python", "api_server.py"]
