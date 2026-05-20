import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { nextTick } from 'vue';

vi.mock('../api/skill', () => ({
  listAgentSkills: vi.fn(),
  createCustomSkill: vi.fn(),
  updateCustomSkill: vi.fn(),
  deleteCustomSkill: vi.fn(),
  importGlobalSkills: vi.fn(),
}));

vi.mock('../store/user', () => ({
  useUserStore: () => ({ user: { userId: 'u-1', role: 'admin' } }),
}));

import * as skillApi from '../api/skill';

const fakePage = (items: any[]) => ({
  items,
  pagination: { totalItems: items.length, page: 1, perPage: 20 },
});

const skill = (k: string, v: 'global' | 'private' = 'global') => ({
  skillId: 'id-' + k,
  skillKey: k,
  name: k.toUpperCase(),
  description: 'desc',
  triggersText: null,
  toolWhitelist: [],
  planTemplate: {},
  inputsSchema: {},
  outputsSchema: {},
  visibility: v,
  ownerUserId: null,
  createdAt: '',
  updatedAt: '',
});

const loadComposable = async () => await import('./useAgentSkills');

describe('useAgentSkills', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(async () => {
    const { __resetForTests } = await loadComposable();
    __resetForTests();
    vi.useRealTimers();
  });

  it('loadMarketplace populates marketplace.value', async () => {
    vi.mocked(skillApi.listAgentSkills).mockResolvedValueOnce(fakePage([skill('a'), skill('b')]));
    const { default: useAgentSkills } = await loadComposable();
    const { marketplace, loadMarketplace } = useAgentSkills();
    await loadMarketplace();
    expect(marketplace.value?.items.length).toBe(2);
    expect(marketplace.value?.items[0].skillKey).toBe('a');
  });

  it('setting queryText debounces and reloads both lists once', async () => {
    vi.mocked(skillApi.listAgentSkills).mockResolvedValue(fakePage([]));
    const { default: useAgentSkills } = await loadComposable();
    const { queryText } = useAgentSkills();
    vi.mocked(skillApi.listAgentSkills).mockClear();
    queryText.value = 'foo';
    queryText.value = 'foobar';
    await nextTick();
    // Not called yet (debounced)
    expect(skillApi.listAgentSkills).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(260);
    // Called twice — one marketplace, one mySkills
    expect(skillApi.listAgentSkills).toHaveBeenCalledTimes(2);
  });

  it('createSkill calls createCustomSkill then reloads mySkills', async () => {
    vi.mocked(skillApi.createCustomSkill).mockResolvedValue(skill('new', 'private') as any);
    vi.mocked(skillApi.listAgentSkills).mockResolvedValue(fakePage([skill('new', 'private')]));
    const { default: useAgentSkills } = await loadComposable();
    const { createSkill, mySkills } = useAgentSkills();
    await createSkill({
      name: 'New',
      description: 'd',
      triggersText: null,
      toolWhitelist: [],
      planTemplate: {},
      inputsSchema: {},
      outputsSchema: {},
    });
    expect(skillApi.createCustomSkill).toHaveBeenCalled();
    expect(mySkills.value?.items[0].skillKey).toBe('new');
  });

  it('submitImport parses array form and reloads marketplace', async () => {
    vi.mocked(skillApi.importGlobalSkills).mockResolvedValue({
      results: [{ skillKey: 'a', action: 'created' }],
    });
    vi.mocked(skillApi.listAgentSkills).mockResolvedValue(fakePage([skill('a')]));
    const { default: useAgentSkills } = await loadComposable();
    const { submitImport, importResults } = useAgentSkills();
    await submitImport({
      mode: 'upsert',
      jsonText: JSON.stringify([{ skillKey: 'a', name: 'A', description: 'd' }]),
    });
    expect(skillApi.importGlobalSkills).toHaveBeenCalled();
    expect(importResults.value.length).toBe(1);
    expect(importResults.value[0].skillKey).toBe('a');
  });
});
