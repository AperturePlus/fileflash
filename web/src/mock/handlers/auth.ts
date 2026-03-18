import Mock from 'mockjs';

export const setupAuthMocks = () => {
  // 登录接口
  Mock.mock(/\/api\/v1\/auth\/login/, 'post', {
    success: true,
    code: 200,
    message: 'Login successful',
    data: { 
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock-access-token-@datetime',
      tokenType: 'Bearer',
      expiresIn: 3600, 
      refreshToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock-refresh-token-@datetime',
      user: { 
        userId: 'user1', 
        username: 'Demo User', 
        email: 'demo@example.com',
        storageLimit: 107374182400, // 100GB
        storageUsed: 21474836480,   // 20GB
        createdAt: '@datetime'
      } 
    },
  });

  // 刷新令牌接口
  Mock.mock(/\/api\/v1\/auth\/refresh/, 'post', {
    success: true,
    code: 200,
    message: 'Token refreshed successfully',
    data: {
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new-access-token-@datetime',
      tokenType: 'Bearer',
      expiresIn: 3600,
      refreshToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new-refresh-token-@datetime',
      user: {
        userId: 'user1',
        username: 'Demo User',
        email: 'demo@example.com',
        storageLimit: 107374182400,
        storageUsed: 21474836480,
        createdAt: '@datetime'
      }
    }
  });

  // 登出接口
  Mock.mock(/\/api\/v1\/auth\/logout/, 'post', {
    success: true,
    code: 200,
    message: 'Logout successful',
    data: null
  });
}; 