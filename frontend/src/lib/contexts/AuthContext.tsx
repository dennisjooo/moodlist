'use client';

import { createContext, useContext } from 'react';
import { AuthContextType, AuthProviderProps } from '../types/auth';
import { useAuthStore } from '@/lib/store/authStore';
import { useShallow } from 'zustand/shallow';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: AuthProviderProps) {
  const value = useAuthStore(
    useShallow((state) => ({
      user: state.user,
      isLoading: state.isLoading,
      isAuthenticated: state.isAuthenticated,
      isValidated: state.isValidated,
      login: state.login,
      logout: state.logout,
      refreshUser: state.refreshUser,
    }))
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
