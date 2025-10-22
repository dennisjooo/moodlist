import type { ReactNode } from 'react';

export interface User {
    id: number;
    spotify_id: string;
    email?: string;
    display_name: string;
    profile_image_url?: string;
    is_active: boolean;
    created_at: string;
}

export interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    isValidated: boolean;
    login: (accessToken: string, refreshToken: string) => Promise<void>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
}

export interface AuthProviderProps {
    children: ReactNode;
}

export interface CachedAuthData {
    user: User;
    timestamp: number;
}
