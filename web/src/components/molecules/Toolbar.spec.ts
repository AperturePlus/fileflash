import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Toolbar from './Toolbar.vue';

describe('molecules/Toolbar', () => {
  it('renders a horizontal group containing slot content', () => {
    const w = mount(Toolbar, {
      slots: { default: '<button>a</button><button>b</button>' },
    });
    expect(w.findAll('button')).toHaveLength(2);
  });

  it('default role is toolbar', () => {
    const w = mount(Toolbar, { slots: { default: 'x' } });
    expect(w.attributes('role')).toBe('toolbar');
  });

  it('without split slot: no divider rendered', () => {
    const w = mount(Toolbar, { slots: { default: '<button>a</button>' } });
    expect(w.find('.ff-divider').exists()).toBe(false);
  });

  it('with split slot: divider + second group rendered', () => {
    const w = mount(Toolbar, {
      slots: {
        default: '<button>a</button>',
        split: '<button>b</button>',
      },
    });
    expect(w.find('.ff-divider').exists()).toBe(true);
    expect(w.findAll('.ff-toolbar-group')).toHaveLength(2);
    expect(w.findAll('button')).toHaveLength(2);
  });
});
