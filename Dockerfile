# One image, one URL: the Vite build from frontend/ is served by the FastAPI app from backend/.
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 \
    CHROMA_PATH=/srv/chroma_data FRONTEND_DIST=/srv/frontend/dist ANONYMIZED_TELEMETRY=False
WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist /srv/frontend/dist
# Seed ChromaDB at build time so the first request is fast (re-seeds automatically if data/ changes)
RUN python -c "from app.retrieval.chroma_store import ChromaStore; print(ChromaStore().counts())"
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
