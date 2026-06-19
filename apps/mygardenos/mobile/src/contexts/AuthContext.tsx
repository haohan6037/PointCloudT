import React, { createContext, useContext, useEffect, useState } from 'react';
import { auth, AuthUser } from '../services/auth';

type AuthContextType = {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: AuthUser) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const savedToken = await auth.getToken();
      if (savedToken) {
        const { user: fetchedUser } = await auth.getMe(savedToken);
        setUser(fetchedUser);
        setToken(savedToken);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      await auth.clearToken();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (newToken: string, newUser: AuthUser) => {
    await auth.saveToken(newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const logout = async () => {
    await auth.clearToken();
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
