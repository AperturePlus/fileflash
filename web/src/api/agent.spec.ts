import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

vi.mock('../store/user', () => ({
  useUserStore: () => ({ token: 'test-token' }),
}));

import { createAgentSseParser, streamAgentJobEvents } from './agent';
import type { AgentJobEvent } from '../types/agent';

describe('api/agent event stream helpers', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('parses SSE events across multiple chunks', () => {
    const events: AgentJobEvent[] = [];
    const parser = createAgentSseParser((event) => events.push(event));

    parser.feed('event: job.running\n');
    parser.feed(
      'data: {"id":"1","jobId":"j1","taskType":"agent.plan","type":"job.running","status":"running","message":"正在规划","data":{},"timestamp":"2026-05-20T00:00:00Z"}\n\n',
    );
    parser.feed(
      'event: plan.ready\ndata: {"id":"2","jobId":"j1","taskType":"agent.plan","type":"plan.ready","status":"succeeded","message":"计划已生成","data":{"result":{"planHash":"h1"}},"timestamp":"2026-05-20T00:00:01Z"}\n\n',
    );
    parser.flush();

    expect(events).toHaveLength(2);
    expect(events[0].type).toBe('job.running');
    expect(events[1].data.result.planHash).toBe('h1');
  });

  it('throws on stream setup failure so callers can fall back to polling', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    } as Response) as unknown as typeof fetch;

    await expect(streamAgentJobEvents('job-1')).rejects.toThrow('503');
  });
});
