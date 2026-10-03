import React, { createContext, useContext, useEffect, useState } from "react";
import { isSupabaseConfigured, supabase } from "../../lib/supabase";
import { getProfile } from "../../lib/api-client";
import type { UserProfile } from "../../types";

interface AuthUser {
  id: string;
  email: string | null;
  displayName?: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  profile: UserProfile | null;
  token: string | null;
  loading: boolean;
  isConfigured: boolean;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string, displayName?: string) => Promise<void>;
  signInWithOAuth: (provider: "google" | "github") => Promise<void>;
  signInAsDemoUser: (userId: string, email: string, displayName: string) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Helper to load application profile from backend
  const syncProfile = async (accessToken: string) => {
    try {
      const p = await getProfile(accessToken);
      setProfile(p);
    } catch (err) {
      console.warn("Unable to sync backend profile:", err);
    }
  };

  useEffect(() => {
    if (!isSupabaseConfigured) {
      // Check if local demo session is stored
      const savedDemo = localStorage.getItem("studyspace_demo_user");
      if (savedDemo) {
        try {
          const parsed = JSON.parse(savedDemo);
          setUser({ id: parsed.id, email: parsed.email, displayName: parsed.displayName });
          setToken(parsed.token);
          syncProfile(parsed.token);
        } catch {
          localStorage.removeItem("studyspace_demo_user");
        }
      }
      setLoading(false);
      return;
    }

    // 1. Restore active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser({
          id: session.user.id,
          email: session.user.email ?? null,
          displayName: session.user.user_metadata?.full_name ?? null,
        });
        setToken(session.access_token);
        syncProfile(session.access_token);
      }
      setLoading(false);
    });

    // 2. Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session) {
        setUser({
          id: session.user.id,
          email: session.user.email ?? null,
          displayName: session.user.user_metadata?.full_name ?? null,
        });
        setToken(session.access_token);
        await syncProfile(session.access_token);
      } else {
        setUser(null);
        setProfile(null);
        setToken(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signInWithEmail = async (email: string, password: string) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase is not configured yet. Use the local demo switcher below or set VITE_SUPABASE_URL.");
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUpWithEmail = async (email: string, password: string, displayName?: string) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase is not configured yet. Use the local demo switcher below or set VITE_SUPABASE_URL.");
    }
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: displayName,
        },
      },
    });
    if (error) throw error;
  };

  const signInWithOAuth = async (provider: "google" | "github") => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase OAuth is not configured yet. Set VITE_SUPABASE_URL and provider credentials.");
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    });
    if (error) throw error;
  };

  // Helper for automated local testing and manual testing before production keys
  const signInAsDemoUser = (userId: string, email: string, displayName: string) => {
    // Generate a development test token matching DEV_TEST_JWT_SECRET
    // In browser, create a simple unverified dev JWT structure
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({
        sub: userId,
        email,
        aud: "authenticated",
        role: "authenticated",
        user_metadata: { full_name: displayName },
      })
    );
    const demoToken = `${header}.${payload}.devsignature`;

    const demoData = { id: userId, email, displayName, token: demoToken };
    localStorage.setItem("studyspace_demo_user", JSON.stringify(demoData));
    setUser({ id: userId, email, displayName });
    setToken(demoToken);
    syncProfile(demoToken);
  };

  const signOut = async () => {
    localStorage.removeItem("studyspace_demo_user");
    if (isSupabaseConfigured) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setProfile(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        token,
        loading,
        isConfigured: isSupabaseConfigured,
        signInWithEmail,
        signUpWithEmail,
        signInWithOAuth,
        signInAsDemoUser,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
