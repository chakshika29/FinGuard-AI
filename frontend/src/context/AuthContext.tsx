import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../services/api";
import { AuthUser } from "../types";

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("finguard_token"));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkMe = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.get<AuthUser>("/api/auth/me");
        setUser(res.data);
      } catch {
        localStorage.removeItem("finguard_token");
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkMe();
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await api.post<{ access_token: string; user: AuthUser }>("/api/auth/login", {
      username,
      password,
    });
    localStorage.setItem("finguard_token", res.data.access_token);
    setToken(res.data.access_token);
    setUser(res.data.user);
  };

  const logout = () => {
    localStorage.removeItem("finguard_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
