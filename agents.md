# FileFlash Agents Guide

## 1. 目标
- 让后续开发代理在本仓库中稳定地进行前后端协作开发。
- 保证「前端类型定义」「前端 API 封装」「前端 mock」「后端 schema」四者长期一致。

## 2. 目录约定
- 前端 API 封装: `web/src/api`
- 前端接口类型: `web/src/types`
- 前端 mock: `web/src/mock/handlers` + `web/src/mock/state.ts`
- 后端 schema: `app/src/schemas`
- 后端数据库模型: `app/src/models/tables_*.py`

## 3. 接口契约规范
- 统一使用 `camelCase` 字段命名（请求与响应都一致）。
- 统一分页结构:
  - `items: []`
  - `pagination: { totalItems, totalPages, perPage, currentPage, hasPrev, hasNext }`
- 日期时间统一使用 ISO 8601 字符串。
- 标准响应外层保持:
  - `success`
  - `code`
  - `message`
  - `data`
  - `timestamp`（可选）

## 4. 已落地的关键约束
- `GET /storage/summary` 作为前端存储统计统一入口。
- `GET /me/activity-log` 返回标准 `PaginatedData<ActivityItem>`，字段为 camelCase，不再使用 snake_case/date-array 兼容格式。

## 5. 后端 Schema 开发规则
- 在 `app/src/schemas` 中新增或修改模型，优先复用:
  - `common.py` 中的 `CamelModel`
  - `PaginatedData` / `PaginationMeta` / `ApiResponse`
- 所有请求/响应 schema 必须能直接映射前端 `web/src/types`。
- 需要互斥或组合约束时，使用 Pydantic 校验器（例如权限接口 file/folder 与 user/group 的互斥约束）。

## 6. 前端接口改动流程（强制）
1. 修改 `web/src/types` 的接口类型。
2. 修改 `web/src/api` 的请求/返回类型。
3. 同步修改 `web/src/mock/handlers` 的入参与返回结构。
4. 同步修改 `app/src/schemas` 的请求/响应模型。
5. 运行检查命令并确认通过。

## 7. 快速检查清单
- 字段命名是否全部为 camelCase。
- API 返回结构是否与 types 完全一致。
- mock 与 API 是否使用同一端点和同一字段。
- schema 是否覆盖请求体、查询参数、响应体。
- 是否存在仅在单边修改的“悬空字段”。

## 8. 验证命令
- 前端类型检查: `bun run check`（在 `web` 目录）
- 前端构建: `bun run build`（在 `web` 目录）
- 后端测试（如有）: `uv run pytest`（在 `app` 目录）
