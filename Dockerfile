FROM node:24-bookworm-slim AS frontend
WORKDIR /web
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_ENV=production LOCAL_DEMO=0 FRONTEND_DIST=/app/frontend
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /web/dist ./frontend
RUN useradd --create-home workspace && chown -R workspace:workspace /app
USER workspace
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
