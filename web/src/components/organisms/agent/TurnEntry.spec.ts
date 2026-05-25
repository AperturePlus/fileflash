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
    timestamp: '2026-05-20T00:00:00Z',
  },
  agent: {
    id: 'a-1',
    role: 'agent',
    content: '',
    status: 'succeeded',
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
