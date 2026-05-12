import { describe, it, expect } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../../test/mount';
import AuthForm from './AuthForm.vue';

const loginLabels = {
  identifier: 'Username or Email', identifierPlaceholder: 'Enter username or email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  rememberMe: 'Remember me',
};
const registerLabels = {
  username: 'Username', usernamePlaceholder: 'Enter username',
  email: 'Email', emailPlaceholder: 'Enter email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  confirmPassword: 'Confirm', confirmPasswordPlaceholder: 'Re-enter password',
};
const forgotLabels = {
  email: 'Email', emailPlaceholder: 'Enter email',
};

describe('AuthForm', () => {
  it('renders title and subtitle', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 'Sign in', subtitle: 'Manage files',
        submitLabel: 'SIGN IN', labels: loginLabels,
      },
    });
    expect(wrapper.text()).toContain('Sign in');
    expect(wrapper.text()).toContain('Manage files');
  });

  it('emits submit with login payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 'Sign in', submitLabel: 'SIGN IN', labels: loginLabels,
      },
    });
    const text = wrapper.find('input[type="text"]');
    const pw = wrapper.find('input[type="password"]');
    const cb = wrapper.find('input[type="checkbox"]');
    await text.setValue('alice');
    await pw.setValue('hunter2');
    await cb.setValue(true);
    await wrapper.find('form').trigger('submit.prevent');
    const evt = wrapper.emitted('submit');
    expect(evt).toBeTruthy();
    expect(evt?.[0]?.[0]).toEqual({
      mode: 'login',
      values: { identifier: 'alice', password: 'hunter2', rememberMe: true },
    });
  });

  it('emits submit with register payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'register', title: 'Sign up', submitLabel: 'REGISTER', labels: registerLabels,
      },
    });
    const text = wrapper.find('input[type="text"]');
    const email = wrapper.find('input[type="email"]');
    const passwords = wrapper.findAll('input[type="password"]');
    expect(passwords.length).toBe(2);
    await text.setValue('bob');
    await email.setValue('bob@example.com');
    await passwords[0].setValue('pw1');
    await passwords[1].setValue('pw2');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      mode: 'register',
      values: { username: 'bob', email: 'bob@example.com', password: 'pw1', confirmPassword: 'pw2' },
    });
  });

  it('emits submit with forgot payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 'Forgot', submitLabel: 'SEND', labels: forgotLabels,
      },
    });
    const email = wrapper.find('input[type="email"]');
    await email.setValue('carol@example.com');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      mode: 'forgot', values: { email: 'carol@example.com' },
    });
  });

  it('renders errorMessage in role=status', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        errorMessage: 'Email not found',
      },
    });
    const status = wrapper.find('[role="status"]');
    expect(status.exists()).toBe(true);
    expect(status.text()).toContain('Email not found');
    expect(status.classes()).toContain('ff-auth__msg--error');
  });

  it('renders successMessage in role=status', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        successMessage: 'Email sent',
      },
    });
    const status = wrapper.find('[role="status"]');
    expect(status.exists()).toBe(true);
    expect(status.text()).toContain('Email sent');
    expect(status.classes()).toContain('ff-auth__msg--success');
  });

  it('disables submit button when isSubmitting is true', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        isSubmitting: true,
      },
    });
    const btn = wrapper.find('button[type="submit"]');
    expect((btn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it('prefills login fields from initial prop', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 't', submitLabel: 'go', labels: loginLabels,
        initial: { identifier: 'alice', rememberMe: true },
      },
    });
    await nextTick();
    const text = wrapper.find('input[type="text"]');
    const cb = wrapper.find('input[type="checkbox"]');
    expect((text.element as HTMLInputElement).value).toBe('alice');
    expect((cb.element as HTMLInputElement).checked).toBe(true);
  });

  it('toggles password visibility via eye button', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 't', submitLabel: 'go', labels: loginLabels,
      },
    });
    const pwInput = wrapper.find('input[type="password"]');
    expect(pwInput.exists()).toBe(true);
    await wrapper.find('[data-test="toggle-password"]').trigger('click');
    expect(wrapper.find('input[type="password"]').exists()).toBe(false);
    expect(wrapper.find('input[type="text"]').exists()).toBe(true);
  });
});
