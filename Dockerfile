# ---------- frontend builder ----------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- backend ----------
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir -e ./backend

COPY backend/ ./backend/
COPY --from=frontend /app/out ./frontend/out

WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -u -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
