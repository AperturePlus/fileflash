import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SessionList from './SessionList.vue';
import type { Session } from '../../../composables/useAgentSession';

const session = (id: string, title = 'X'): Session => ({
  id,
  title,
  messages: [],
  createdAt: '2026-05-20T00:00:00Z',
  updatedAt: '2026-05-20T00:00:00Z',
});

describe('organisms/agent/SessionList', () => {
  it('renders empty placeholder when no sessions', () => {
    const w = mount(SessionList, { props: { sessions: [], activeId: null } });
    expect(w.text()).toContain('暂无会话');
  });

  it('emits select with id when an item is clicked', async () => {
    const w = mount(SessionList, {
      props: { sessions: [session('a'), session('b')], activeId: 'a' },
    });
    const items = w.findAll('.ff-si');
    expect(items.length).toBe(2);
    await items[1].trigger('click');
    expect(w.emitted('select')?.[0]).toEqual(['b']);
  });

  it('+ button emits create', async () => {
    const w = mount(SessionList, { props: { sessions: [], activeId: null } });
    await w.find('header button').trigger('click');
    expect(w.emitted('create')).toHaveLength(1);
  });
});
