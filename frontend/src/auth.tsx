import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, type User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    password: string,
    name: string,
    targetBandOverall: number | null,
    targetBandWriting: number | null,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("prepsathi_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => localStorage.removeItem("prepsathi_token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const { access_token } = await api.login(email, password);
    localStorage.setItem("prepsathi_token", access_token);
    setUser(await api.me());
  }

  async function signup(
    email: string,
    password: string,
    name: string,
    targetBandOverall: number | null,
    targetBandWriting: number | null,
  ) {
    const { access_token } = await api.signup({
      email,
      password,
      name,
      target_band_overall: targetBandOverall,
      target_band_writing: targetBandWriting,
    });
    localStorage.setItem("prepsathi_token", access_token);
    setUser(await api.me());
  }

  function logout() {
    localStorage.removeItem("prepsathi_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
