import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  // Login user
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const rawText = await response.text();
        let errorMessage = 'Login failed';
        if (rawText) {
          try {
            const errorData = JSON.parse(rawText);
            errorMessage = errorData.detail || errorMessage;
          } catch (parseError) {
            errorMessage = rawText;
          }
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const { access_token, user } = data;

      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(user));

      setToken(access_token);
      setUser(user);

      return data;
    } catch (err) {
      const errorMsg = err.message || 'Login failed';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register new user
  const register = async (username, email, password, role = 'recruiter') => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, role })
      });

      if (!response.ok) {
        const rawText = await response.text();
        let errorMessage = 'Registration failed';
        if (rawText) {
          try {
            const errorData = JSON.parse(rawText);
            errorMessage = errorData.detail || errorMessage;
          } catch (parseError) {
            errorMessage = rawText;
          }
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const { access_token, user } = data;

      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(user));

      setToken(access_token);
      setUser(user);

      return data;
    } catch (err) {
      const errorMsg = err.message || 'Registration failed';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout user
  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setToken(null);
    setUser(null);
  };

  // Refresh token
  const refreshToken = async () => {
    if (!token) return;

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      const { access_token, user } = data;

      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(user));

      setToken(access_token);
      setUser(user);

      return data;
    } catch (err) {
      // If refresh fails, logout user
      logout();
      throw err;
    }
  };

  // Check if user has a specific role
  const hasRole = (requiredRole) => {
    if (!user) return false;
    if (Array.isArray(requiredRole)) {
      return requiredRole.includes(user.role);
    }
    return user.role === requiredRole;
  };

  // Check if user has a specific permission
  const hasPermission = (permission) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes(permission);
  };

  // Check if user has any of the required permissions
  const hasAnyPermission = (permissions) => {
    if (!user || !user.permissions) return false;
    return permissions.some(p => user.permissions.includes(p));
  };

  // Check if user has all of the required permissions
  const hasAllPermissions = (permissions) => {
    if (!user || !user.permissions) return false;
    return permissions.every(p => user.permissions.includes(p));
  };

  // Social login/register
  const loginSocial = async (credential, provider, role = 'recruiter', mode = 'login') => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/social', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential, provider, role, mode })
      });

      if (!response.ok) {
        const rawText = await response.text();
        let errorMessage = 'Social login failed';
        if (rawText) {
          try {
            const errorData = JSON.parse(rawText);
            errorMessage = errorData.detail || errorMessage;
          } catch (parseError) {
            errorMessage = rawText;
          }
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const { access_token, user } = data;

      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(user));

      setToken(access_token);
      setUser(user);

      return data;
    } catch (err) {
      setError(err.message || 'Social login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    token,
    loading,
    error,
    login,
    register,
    loginSocial,
    logout,
    refreshToken,
    hasRole,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isAuthenticated: !!user && !!token
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
