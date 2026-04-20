import Mock from 'mockjs';
import { addLog, addNotification, createMockId, getCurrentUser, mockUsers, setCurrentUser } from '../state';

let activeRefreshSessionUserId: string | null = null;
const verificationTokenMap = new Map<string, string>();

function buildUserPayload(user: (typeof mockUsers)[number]) {
  return {
    userId: user.userId,
    username: user.username,
    email: user.email,
    storageLimit: user.storageLimit,
    storageUsed: user.storageUsed,
    emailVerified: user.emailVerified,
    emailVerifiedAt: user.emailVerifiedAt,
    createdAt: user.createdAt,
    role: user.role,
    status: user.status,
    preference: user.preference,
  };
}

function issueVerificationToken(userId: string) {
  const token = `verify-${createMockId('token')}`;
  verificationTokenMap.set(token, userId);
  return token;
}

export const setupAuthMocks = () => {
  Mock.mock(/\/api\/v1\/auth\/login/, 'post', (options) => {
    const { username, password } = JSON.parse(options.body || '{}');
    const targetUser = mockUsers.find((user) =>
      user.username.toLowerCase() === String(username || '').toLowerCase() ||
      user.email.toLowerCase() === String(username || '').toLowerCase(),
    );

    if (!targetUser || !password || targetUser.password !== password) {
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

    setCurrentUser(targetUser.userId);
    activeRefreshSessionUserId = targetUser.userId;
    addLog('user_login', { userId: targetUser.userId, username: targetUser.username });

    return {
      success: true,
      code: 200,
      message: 'Login successful',
      data: {
        token: `mock-access-${createMockId('token')}`,
        tokenType: 'Bearer',
        expiresIn: 900,
        user: buildUserPayload(targetUser),
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/register/, 'post', (options) => {
    const { username, email, password } = JSON.parse(options.body || '{}');

    if (!username || !email || !password) {
      return {
        success: false,
        code: 400,
        message: 'Username, email and password are required',
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

    const createdAt = new Date().toISOString();
    const createdUser = {
      userId: createMockId('user'),
      username,
      email,
      storageLimit: 50 * 1024 * 1024 * 1024,
      storageUsed: 0,
      emailVerified: false,
      emailVerifiedAt: null,
      createdAt,
      status: 'active' as const,
      role: 'user' as const,
      password,
      preference: {
        language: 'zh-CN' as const,
      },
    };

    mockUsers.push(createdUser);

    const token = issueVerificationToken(createdUser.userId);
    addLog('user_register', { userId: createdUser.userId, email: createdUser.email });
    addNotification(`Registration email sent to ${createdUser.email}, token=${token}`, true);

    return {
      success: true,
      code: 201,
      message: 'Registration successful',
      data: {
        user: buildUserPayload(createdUser),
        emailVerificationRequired: true,
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
        expiresInMinutes: 30,
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
    const user = getCurrentUser();
    if (!activeRefreshSessionUserId || activeRefreshSessionUserId !== user.userId) {
      return {
        success: false,
        code: 401,
        message: 'Invalid or expired refresh token',
        data: null,
      };
    }
    return {
      success: true,
      code: 200,
      message: 'Token refreshed successfully',
      data: {
        token: `mock-access-${createMockId('token')}`,
        tokenType: 'Bearer',
        expiresIn: 900,
        user: buildUserPayload(user),
      },
    };
  });

  Mock.mock(/\/api\/v1\/auth\/verify-email/, 'post', (options) => {
    const { token } = JSON.parse(options.body || '{}');
    const userId = verificationTokenMap.get(String(token || ''));
    if (!userId) {
      return {
        success: false,
        code: 400,
        message: 'Invalid or expired verification token',
        data: null,
      };
    }

    const targetUser = mockUsers.find((item) => item.userId === userId);
    if (!targetUser) {
      return {
        success: false,
        code: 404,
        message: 'User not found',
        data: null,
      };
    }

    verificationTokenMap.delete(String(token));
    targetUser.emailVerified = true;
    targetUser.emailVerifiedAt = new Date().toISOString();
    addLog('user_email_verified', { userId: targetUser.userId });

    return {
      success: true,
      code: 200,
      message: 'Email verified successfully',
      data: null,
    };
  });

  Mock.mock(/\/api\/v1\/auth\/resend-verification/, 'post', () => {
    const user = getCurrentUser();
    if (user.emailVerified) {
      return {
        success: true,
        code: 200,
        message: 'Email already verified',
        data: null,
      };
    }

    const token = issueVerificationToken(user.userId);
    addNotification(`Verification email resent to ${user.email}, token=${token}`, true);
    addLog('user_email_verification_resent', { userId: user.userId });
    return {
      success: true,
      code: 200,
      message: 'Verification email sent',
      data: null,
    };
  });

  Mock.mock(/\/api\/v1\/auth\/logout/, 'post', () => {
    activeRefreshSessionUserId = null;
    setCurrentUser(mockUsers[0].userId);
    addLog('user_logout', { status: 'ok' });

    return {
      success: true,
      code: 200,
      message: 'Logout successful',
      data: null,
    };
  });
};

