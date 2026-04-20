# FileFlash AGENTS Guide

## 1. 目标

- 让后续开发代理在本仓库进行稳定的前后端协同开发。
- 保证「前端类型」「前端 API」「前端 mock」「后端 schema/路由」长期一致。
- 所有新增能力默认可测试、可回归、可追踪（日志/事件）。

## 2. 代码结构与职责

- 前端 API 封装: `web/src/api`
- 前端类型定义: `web/src/types`
- 前端 mock: `web/src/mock/handlers` + `web/src/mock/state.ts`
- 前端鉴权状态: `web/src/store/user.ts`
- 后端入口: `app/src/main.py`
- 后端路由: `app/src/routers`
- 后端服务层: `app/src/services`
- 后端依赖/鉴权: `app/src/core/deps.py`
- 后端 schema: `app/src/schemas`
- 后端模型: `app/src/models/tables_*.py`
- 数据库会话: `app/src/db`

## 3. 全局接口契约

- 字段命名统一 `camelCase`（请求和响应都一致）。
- 统一响应壳:
  - `success`
  - `code`
  - `message`
  - `data`
  - `timestamp`
- 统一分页结构:
  - `items: []`
  - `pagination: { totalItems, totalPages, perPage, currentPage, hasPrev, hasNext }`
- 日期时间统一 ISO 8601 字符串。

## 4. 鉴权模块基线（当前已落地）

- Access Token:
  - 响应体返回 `token/tokenType/expiresIn/user`
  - 通过 `Authorization: Bearer <token>` 访问受保护接口
  - 默认 TTL: 15 分钟
- Refresh Token:
  - 仅放 `HttpOnly Cookie`（禁止放前端 localStorage/sessionStorage）
  - 服务端仅存 `refreshToken hash` 到 `user_session`
  - `/auth/refresh` 做 rotation（旧 refresh 失效）
  - 默认 TTL: 7 天
- 邮箱验证策略:
  - 允许未验证用户登录
  - 未验证用户仅允许认证相关接口 + `/me/profile`
  - 其他业务接口默认拦截 403（见验证门禁中间件）
- 限流策略（Redis）:
  - 注册/登录/找回密码/重发验证邮件均做限流
  - Redis 不可用时可降级，但不得放开核心认证校验

## 5. 后端开发规则

- 一律优先异步实现:
  - 路由函数 `async def`
  - `AsyncSession` + 异步 SQLAlchemy 查询
- 业务逻辑放 `services`，路由只做参数编排与响应组装。
- 新增接口时必须使用统一响应壳，不直接裸返回 dict。
- 认证相关变更必须同步检查:
  - Cookie 设置项（`httpOnly/secure/sameSite/path/maxAge`）
  - Token TTL 配置
  - `user_session` 的创建/轮换/撤销
- 用户状态对外暴露保持前端语义:
  - `active | suspended`
  - 内部枚举差异在服务层映射，不把内部状态直接泄露给前端。

## 6. 前端开发规则

- 任何接口变更必须同时修改:
  1. `web/src/types`
  2. `web/src/api`
  3. `web/src/mock/handlers` + `web/src/mock/state.ts`
  4. 对应页面/store
  5. 后端 `app/src/schemas` + `app/src/routers/services`
- 鉴权状态规则:
  - 仅持久化 `accessToken`（当前策略）
  - 刷新流程依赖 Cookie（`axios.withCredentials = true`）
  - 登录后若 `emailVerified=false`，跳转 `/verify-email`

## 7. RabbitMQ 接入约定（当前为预留）

- 通过发布器抽象接入（当前 in-process publisher）。
- 后续接 RabbitMQ 时:
  - 不改服务层方法签名
  - 只替换发布器实现
  - 事件名称保持稳定（如 `auth.user_logged_in`, `auth.password_reset_requested`）

## 8. 变更前后检查清单

- 是否仍满足 `types -> api -> mock -> schema -> router/service` 一致性。
- 是否新增了“悬空字段”（只改单边）。
- 是否破坏响应壳结构或 camelCase 命名。
- 是否引入同步 DB 调用或阻塞操作到异步路径。
- 是否错误地把 refreshToken 暴露给前端。
- 是否覆盖未验证邮箱门禁策略。

## 9. 验证命令

- 前端类型检查: `bun run check`（`web` 目录）
- 前端构建: `bun run build`（`web` 目录）
- 后端测试: `uv run pytest`（`app` 目录）
- 后端启动冒烟: `uv run python -c "from src.main import app; print(app.title)"`（`app` 目录）

## 10. 安全与配置要求

- 严禁提交真实密钥/口令到仓库（邮件、JWT、数据库、Redis 等）。
- 新环境统一从 `app/src/.env.example` 拷贝并填充。
- 生产环境必须替换 `JWT_SECRET_KEY` 为高强度随机值（>=32 bytes）。
