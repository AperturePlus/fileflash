import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import UploadProgressTray from './UploadProgressTray.vue';

const tasks = [
  { id: 't1', name: 'video.mp4', progress: { percentage: 42 } },
  { id: 't2', name: 'doc.pdf', progress: { percentage: 100 } },
];

describe('UploadProgressTray', () => {
  it('renders nothing when tasks list is empty', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks: [] } });
    expect(wrapper.find('.tray').exists()).toBe(false);
  });

  it('renders one row per task with name + percentage', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks } });
    expect(wrapper.findAll('.tray__row')).toHaveLength(2);
    expect(wrapper.text()).toContain('video.mp4');
    expect(wrapper.text()).toContain('42');
    expect(wrapper.text()).toContain('100');
  });

  it('shows the queue length in the header', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks } });
    expect(wrapper.find('.tray__head').text()).toMatch(/2/);
  });
});
