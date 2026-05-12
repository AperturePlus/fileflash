# FileFlash Workers 设计文档

## 1. 目标

- 将 CPU 密集任务从 API 请求线程移出，避免阻塞 FastAPI 主事件循环。
- 通过 RabbitMQ 解耦「请求入口」与「任务执行」，提升系统吞吐与稳定性。
- 保证任务执行具备可追踪、可重试、可恢复能力。

## 2. 范围

- 本文覆盖 worker 进程设计、消息模型、重试机制、幂等策略、部署方式。
- 本文不覆盖具体业务算法实现（如转码参数细节、内容扫描引擎细节）。

## 3. 总体架构

- API 服务：校验请求、写入 `background_job`、发布消息（建议 Outbox 模式）。
- RabbitMQ：任务路由、排队、重试、死信。
- Worker 服务：消费任务并执行 CPU 密集逻辑，更新任务状态与结果。
- 数据库：保存任务状态、结果、错误信息、重试元数据。

## 4. 目录与代码组织

- `app/src/workers/bootstrap.py`: 连接 MQ、初始化 worker runtime。
- `app/src/workers/consumer.py`: 消费循环、ACK/NACK、状态编排。
- `app/src/workers/dispatcher.py`: 根据 `taskType` 分发到具体任务处理器。
- `app/src/tasks/registry.py`: 任务注册表（`taskType -> handler`）。
- `app/src/tasks/*.py`: 具体 CPU 任务实现（preview/scan/transcode/hash）。

## 5. 队列拓扑（推荐）

- Exchange: `fileflash.tasks`（topic）
- 主队列:
  - `task.preview`
  - `task.scan`
  - `task.transcode`
  - `task.hash`
- 每个主队列对应:
  - `task.<name>.retry`（TTL + 回流主队列）
  - `task.<name>.dlq`（死信队列）

## 6. 消息协议

```json
{
  "version": 1,
  "messageId": "uuid",
  "jobId": "uuid",
  "taskType": "preview.generate",
  "idempotencyKey": "file:{fileId}:preview:v1",
  "attempt": 0,
  "maxAttempts": 5,
  "traceId": "uuid",
  "requestedBy": "userId",
  "payload": {
    "fileId": "123",
    "objectId": "456"
  }
}
```

## 7. 任务状态机

- `pending`: 已创建，待执行。
- `running`: worker 已接单并开始执行。
- `succeeded`: 执行成功，结果已写库。
- `retrying`: 本次失败，等待重试窗口。
- `failed`: 达到最大重试或不可恢复错误。
- `canceled`: 被用户或系统取消。

状态迁移规则：

- worker 拿到消息后先将任务置为 `running`。
- 任务成功后写 `succeeded`，再 ACK。
- 任务失败若可重试，写 `retrying` 并进入 retry queue。
- 超重试上限或不可恢复错误写 `failed`，进入 DLQ。

## 8. Worker 执行模型

- consumer 层保持异步 I/O（MQ/DB）。
- CPU 任务层使用进程并发，避免 GIL 限制。
- 推荐两种方式：
  - 方式 A：一个 worker 进程 + `ProcessPoolExecutor`
  - 方式 B：多个 worker 进程（每进程单任务并发）

建议默认：

- `prefetch_count = 10`
- `worker_concurrency = CPU 核心数或核心数-1`

## 9. 幂等与一致性

- 幂等键：`idempotencyKey` 必须唯一。
- 业务副作用（写文件/写结果）前先检查是否已处理完成。
- ACK 时机：仅在结果成功持久化后 ACK。
- 推荐使用 Outbox 保证「数据库提交」与「消息发送」一致性。

## 10. 错误与重试策略

- 可恢复错误：网络抖动、临时依赖故障 -> 重试。
- 不可恢复错误：参数非法、资源不存在 -> 直接失败。
- 重试退避建议：`30s -> 2m -> 10m -> 30m -> 2h`。
- 达到上限后写 `failed` 并投递 DLQ，等待人工处理。

## 11. 可观测性

- 日志字段最少包含：`jobId`, `taskType`, `traceId`, `attempt`, `durationMs`, `status`。
- 指标建议：
  - 队列积压长度
  - 消费速率
  - 成功率/失败率
  - 平均执行时长
  - DLQ 增量
- 告警建议：
  - DLQ 持续增长
  - 平均执行时长异常抬升
  - retrying 比例异常

## 12. 配置项（建议）

- `RABBITMQ_URL`
- `MQ_PREFETCH`
- `WORKER_CONCURRENCY`
- `JOB_DEFAULT_MAX_ATTEMPTS`
- `RETRY_BASE_SECONDS`
- `WORKER_SHUTDOWN_TIMEOUT_SECONDS`

## 13. 启动与部署建议

- 同仓库、分进程部署：
  - API 进程：`uv run python -m fileflash.main`
  - Worker 进程：`uv run python -m fileflash.workers.consumer`
- 多 worker 副本按队列水平扩容。
- 当前阶段属于分布式单体，不是严格微服务。

## 14. 实施顺序（建议）

1. 落库 `background_job` + `outbox_event` 表。
2. 实现 publisher 与 outbox relay。
3. 实现基础 consumer 与 dispatcher。
4. 打通一个试点任务（建议 preview.generate）。
5. 完成 retry/dlq 与监控告警。
6. 逐步迁移其他 CPU 任务。
