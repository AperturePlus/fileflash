import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SkillCard from './SkillCard.vue';
import type { AgentSkillItem } from '../../../types/skill';

const skill: AgentSkillItem = {
  skillId: 'id-1',
  skillKey: 'org.tidy',
  name: 'Tidy',
  description: 'Organize files',
  triggersText: 'organize',
  toolWhitelist: [],
  planTemplate: {},
  inputsSchema: {},
  outputsSchema: {},
  visibility: 'private',
  ownerUserId: 'u-1',
  createdAt: '',
  updatedAt: '',
};

describe('organisms/agent/SkillCard', () => {
  it('renders skill.name and skill.skillKey', () => {
    const w = mount(SkillCard, { props: { skill } });
    expect(w.text()).toContain('Tidy');
    expect(w.text()).toContain('org.tidy');
  });

  it('editable=true shows Edit + Delete buttons; clicks emit', async () => {
    const w = mount(SkillCard, { props: { skill, editable: true } });
    const buttons = w.findAll('button');
    expect(buttons.length).toBeGreaterThanOrEqual(2);
    const edit = buttons.find((b) => /edit/i.test(b.text()))!;
    const del = buttons.find((b) => /delete/i.test(b.text()))!;
    await edit.trigger('click');
    await del.trigger('click');
    expect(w.emitted('edit')).toHaveLength(1);
    expect(w.emitted('delete')).toHaveLength(1);
  });

  it('editable=false shows neither button', () => {
    const w = mount(SkillCard, { props: { skill, editable: false } });
    const buttons = w.findAll('button');
    expect(buttons.length).toBe(0);
  });
});
