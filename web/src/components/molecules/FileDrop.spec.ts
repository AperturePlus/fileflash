import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import FileDrop from './FileDrop.vue';

const makeFile = (name: string, type = 'text/plain') =>
  new File([new Blob(['x'])], name, { type });

describe('molecules/FileDrop', () => {
  it('renders default helper text and accepts slot override', () => {
    const a = mount(FileDrop);
    expect(a.text()).toMatch(/drop file|click/i);
    const b = mount(FileDrop, { slots: { default: 'Upload JSON here' } });
    expect(b.text()).toContain('Upload JSON here');
  });

  it('change on hidden input with one file emits files[]', async () => {
    const w = mount(FileDrop);
    const file = makeFile('a.txt');
    const input = w.find('input[type="file"]').element as HTMLInputElement;
    Object.defineProperty(input, 'files', {
      value: [file],
      configurable: true,
    });
    await w.find('input[type="file"]').trigger('change');
    expect(w.emitted('files')?.[0]).toEqual([[file]]);
  });

  it('drop event with dataTransfer.files emits files', async () => {
    const w = mount(FileDrop);
    const file = makeFile('a.txt');
    await w.find('.ff-drop').trigger('drop', {
      dataTransfer: { files: [file] },
    });
    expect(w.emitted('files')?.[0]).toEqual([[file]]);
  });

  it('multiple=false drops 2 files but emits only first', async () => {
    const w = mount(FileDrop, { props: { multiple: false } });
    const f1 = makeFile('a.txt');
    const f2 = makeFile('b.txt');
    await w.find('.ff-drop').trigger('drop', {
      dataTransfer: { files: [f1, f2] },
    });
    expect(w.emitted('files')?.[0]).toEqual([[f1]]);
  });
});
