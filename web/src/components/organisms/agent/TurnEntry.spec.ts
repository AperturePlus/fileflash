import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import TurnEntry from './TurnEntry.vue';
import type { AgentTurn } from '../../../composables/useAgentSession';

const baseTurn = (overrides: Partial<AgentTurn['agent']> = {}): AgentTurn => ({
  user: {
    id: 'u-1',
    role: 'user',
    content: 'do it',
    status: 'succeeded',
    events: [],
    timestamp: '2026-05-20T00:00:00Z',
  },
  agent: {
    id: 'a-1',
    role: 'agent',
    content: '',
    status: 'succeeded',
    events: [],
    timestamp: '2026-05-20T00:00:00Z',
    planHash: 'hash-1',
    planResult: {
      planJobId: 'p-1',
      planHash: 'hash-1',
      chosenSkill: null,
      proposedActions: [],
      summary: 'plan summary text',
      requiresConfirmation: false,
      costEstimate: { tokens: 100, toolCalls: 2, durationSecEstimate: 5 },
    },
    ...overrides,
  },
});

describe('organisms/agent/TurnEntry', () => {
  it('renders the plan summary text', () => {
    const w = mount(TurnEntry, {
      props: { turn: baseTurn(), policy: 'confirm', focused: false },
    });
    expect(w.text()).toContain('plan summary text');
  });

  it('renders execution answer before the plan summary', () => {
    const w = mount(TurnEntry, {
      props: {
        turn: baseTurn({
          executeResult: {
            planJobId: 'p-1',
            executeJobId: 'e-1',
            summary: 'execution summary text',
            answer: '你上传了 3 部电影（按视频文件统计）。',
            appliedActions: 1,
            skippedActions: 0,
            warnings: [],
            finishedAt: '2026-05-20T00:01:00Z',
          },
        }),
        policy: 'confirm',
        focused: false,
      },
    });
    expect(w.text()).toContain('3 部电影');
    expect(w.text()).not.toContain('plan summary text');
  });

  it('renders lightweight agent activity events before the answer', () => {
    const w = mount(TurnEntry, {
      props: {
        turn: baseTurn({
          events: [
            {
              id: 'ev-1',
              jobId: 'e-1',
              taskType: 'agent.execute',
              type: 'tool.started',
              status: 'running',
              agentPhase: 'executing',
              message: '正在读取名称包含“银翼杀手”的视频文件数量。',
              data: {},
              timestamp: '2026-05-20T00:00:01Z',
            },
          ],
          executeResult: {
            planJobId: 'p-1',
            executeJobId: 'e-1',
            summary: 'execution summary text',
            answer: '你上传了 2 部名称包含“银翼杀手”的电影（按视频文件统计）。',
            appliedActions: 1,
            skippedActions: 0,
            warnings: [],
            finishedAt: '2026-05-20T00:01:00Z',
          },
        }),
        policy: 'confirm',
        focused: false,
      },
    });

    expect(w.text()).toContain('正在读取名称包含');
    expect(w.text()).toContain('你上传了 2 部名称包含');
  });

  it('hides Execute button when policy=planOnly', () => {
    const w = mount(TurnEntry, {
      props: { turn: baseTurn(), policy: 'planOnly', focused: false },
    });
    const buttons = w.findAll('button').map((b) => b.text());
    expect(buttons.some((label) => /execute|执行/i.test(label))).toBe(false);
  });

  it('hides Execute button once executeJobId is assigned', () => {
    const w = mount(TurnEntry, {
      props: {
        turn: baseTurn({ executeJobId: 'exec-1' }),
        policy: 'confirm',
        focused: false,
      },
    });
    const buttons = w.findAll('button').map((b) => b.text());
    expect(buttons.some((label) => /execute|执行/i.test(label))).toBe(false);
  });

  it('Cancel button present when running, clicking emits cancel', async () => {
    const w = mount(TurnEntry, {
      props: { turn: baseTurn({ status: 'running' }), policy: 'confirm', focused: false },
    });
    const cancelBtn = w.findAll('button').find((b) => /cancel|取消/i.test(b.text()));
    expect(cancelBtn).toBeTruthy();
    await cancelBtn!.trigger('click');
    expect(w.emitted('cancel')).toHaveLength(1);
  });
});
