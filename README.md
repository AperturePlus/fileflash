# FileFlash

FileFlash 是一个面向个人与团队的现代文件工作台：上传、管理、预览、分享、回收站、后台治理与 Agent 工作流集中在一个清爽的 Web / Desktop 体验里。

## Highlights

- 文件云盘：文件夹、批量操作、拖拽上传、分片上传、下载与回收站
- 在线预览：图片、PDF、音视频、压缩包等常见文件类型
- 安全分享：公开分享链接、访问控制、分享中心与接收列表
- 管理后台：用户、存储、内容审核、日志、通知、系统状态与注册规则
- Agent 工作区：任务会话、技能管理、计划执行与事件追踪
- 自托管优先：PostgreSQL + Redis + MinIO，后端异步 API，前端支持 Web 与 Electron

## Tech Stack

- Frontend: Vue 3, Vite, TypeScript, Pinia, Naive UI, Vitest
- Desktop: Electron
- Backend: FastAPI, Pydantic, SQLAlchemy Async, PostgreSQL
- Infra: Redis, MinIO, Flyway, uv, Bun

## Quick Start

### 1. Start dependencies

```bash
cd docker/postgresql-16
docker compose up -d

cd ../redis
docker compose up -d

cd ../minio
docker compose up -d
```

PostgreSQL compose includes Flyway migration. MinIO console runs at `http://localhost:9001`.

### 2. Configure backend

```bash
cd app
cp .env.example .env
```

Adjust `.env` if needed. For the bundled Docker services, keep database, Redis, and MinIO values aligned with the compose files.

### 3. Start backend

```bash
cd app
uv run fileflash
```

Backend API: `http://localhost:8080`  
Health check: `http://localhost:8080/health`

Development seed accounts:

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| User | `demo` | `demo123` |

### 4. Start frontend

```bash
cd web
bun install
bun run dev
```

Frontend dev server: `http://localhost:5173`

## Common Commands

```bash
# Backend tests
cd app && uv run pytest

# Backend import smoke test
cd app && uv run python -c "from fileflash.main import app; print(app.title)"

# Frontend type check
cd web && bun run check

# Frontend build
cd web && bun run build

# Electron dev
cd web && bun run electron:dev
```

## Project Layout

```text
app/      FastAPI backend, async services, schemas, workers, tests
web/      Vue frontend, API clients, mock handlers, pages, Electron shell
docker/   PostgreSQL/Flyway, Redis, MinIO local infrastructure
docs/     Design notes, implementation plans, project memory
```

## Notes

- API responses use a unified envelope: `success`, `code`, `message`, `data`, `timestamp`.
- Request and response fields use `camelCase`.
- Refresh tokens stay in HttpOnly cookies; the frontend only persists the access token.
- Production deployments must replace secrets in `app/.env`, especially `JWT_SECRET_KEY`.
