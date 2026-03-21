import Mock from 'mockjs';
import { addLog, addNotification, createMockId, mockUsers } from '../state';

export const setupAuthMocks = () => {
  Mock.mock(/\/api\/v1\/auth\/login/, 'post', (options) => {
    const { username, password } = JSON.parse(options.body || '{}');
    const targetUser = mockUsers.find((user) =>
      user.username.toLowerCase() === String(username || '').toLowerCase() ||
      user.email.toLowerCase() === String(username || '').toLowerCase(),
    );

    if (!targetUser || !password) {
      return {
        success: false,
        code: 401,
        message: 'Invalid username or password',
        data: null,
      };
    }

    if (targetUser.status === 'suspended') {
      return {
        success: false,
        code: 403,
        message: 'Account is suspended',
        data: null,
      };
    }

    addLog('user_login', { userId: targetUser.userId, username: targetUser.username });

    return {
      success: true,
      code: 200,
      message: 'Login successful',
      data: {
        token: `mock-access-${createMockId('token')}`,
        tokenType: 'Bearer',
        expiresIn: 3600,
        refreshToken: `mock-refresh-${createMockId('token')}`,
        user: {
          userId: targetUser.userId,
          username: targetUser.username,
          email: targetUser.email,
          storageLimit: targetUser.storageLimit,
          storageUsed: targetUser.storageUsed,
          createdAt: targetUser.createdAt,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/register/, 'post', (options) => {
    const { username, email } = JSON.parse(options.body || '{}');

    if (!username || !email) {
      return {
        success: false,
        code: 400,
        message: 'Username and email are required',
        data: null,
      };
    }

    const exists = mockUsers.some((user) =>
      user.username.toLowerCase() === String(username).toLowerCase() ||
      user.email.toLowerCase() === String(email).toLowerCase(),
    );

    if (exists) {
      return {
        success: false,
        code: 409,
        message: 'User already exists',
        data: null,
      };
    }

    const createdUser = {
      userId: createMockId('user'),
      username,
      email,
      storageLimit: 50 * 1024 * 1024 * 1024,
      storageUsed: 0,
      createdAt: new Date().toISOString(),
      status: 'active' as const,
      role: 'user' as const,
    };

    mockUsers.push(createdUser);

    addLog('user_register', { userId: createdUser.userId, email: createdUser.email });
    addNotification(`Registration email sent to ${createdUser.email}`, true);

    return {
      success: true,
      code: 201,
      message: 'Registration successful',
      data: {
        ...createdUser,
        groups: [],
        updatedAt: createdUser.createdAt,
        lastLogin: createdUser.createdAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/forgot-password/, 'post', (options) => {
    const { email } = JSON.parse(options.body || '{}');

    if (!email) {
      return {
        success: false,
        code: 400,
        message: 'Email is required',
        data: null,
      };
    }

    addLog('password_reset_request', { email });
    addNotification(`Password reset email queued for ${email}`, true);

    return {
      success: true,
      code: 200,
      message: 'If this email exists, a reset link has been sent',
      data: {
        requestId: createMockId('pwd_reset'),
        expiresInMinutes: 15,
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/reset-password/, 'post', () => {
    addLog('password_reset_complete', { status: 'ok' });

    return {
      success: true,
      code: 200,
      message: 'Password has been reset successfully',
      data: null,
    };
  });

  Mock.mock(/\/api\/v1\/auth\/refresh/, 'post', () => {
    return {
      success: true,
      code: 200,
      message: 'Token refreshed successfully',
      data: {
        token: `mock-access-${createMockId('token')}`,
        tokenType: 'Bearer',
        expiresIn: 3600,
        refreshToken: `mock-refresh-${createMockId('token')}`,
        user: {
          userId: mockUsers[0].userId,
          username: mockUsers[0].username,
          email: mockUsers[0].email,
          storageLimit: mockUsers[0].storageLimit,
          storageUsed: mockUsers[0].storageUsed,
          createdAt: mockUsers[0].createdAt,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/logout/, 'post', () => {
    addLog('user_logout', { status: 'ok' });

    return {
      success: true,
      code: 200,
      message: 'Logout successful',
      data: null,
    };
  });
};
