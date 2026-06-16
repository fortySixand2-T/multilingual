import { createContext, useContext, useState, ReactNode } from "react";
import { api, getToken, setToken } from "./api";

type AuthCtx = {
  authed: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (b: { email: string; password: string; invite_code: string; display_name: string }) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState<boolean>(!!getToken());

  const login = async (email: string, password: string) => {
    const { access_token } = await api.login({ email, password });
    setToken(access_token);
    setAuthed(true);
  };
  const signup = async (b: { email: string; password: string; invite_code: string; display_name: string }) => {
    const { access_token } = await api.signup(b);
    setToken(access_token);
    setAuthed(true);
  };
  const logout = () => {
    setToken(null);
    setAuthed(false);
  };

  return <Ctx.Provider value={{ authed, login, signup, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
