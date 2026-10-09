import React, { createContext, useContext, useEffect, useState } from "react";
import type { Session, User as SupabaseUser } from "@supabase/supabase-js";
import { getAuthRedirectUrl, isSupabaseConfigured, supabase } from "../../lib/supabase";
import { getProfile } from "../../lib/api-client";
import type { UserProfile } from "../../types";

export interface AuthUser {
  id: string;
  email: string | null;
  displayName: string | null;
  supabaseUser?: SupabaseUser;
}

export interface AuthContextType {
  user: AuthUser | null;
  session: Session | null;
  profile: UserProfile | null;
  token: string | null;
  loading: boolean;
  isConfigured: boolean;
  isRecoveryMode: boolean;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (
    email: string,
    password: string,
    displayName?: string
  ) => Promise<{ needsConfirmation: boolean }>;
  signInWithOAuth: (provider: "google" | "github") => Promise<void>;
  resetPasswordForEmail: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapSupabaseUser(sbUser: SupabaseUser): AuthUser {
  return {
    id: sbUser.id,
    email: sbUser.email ?? null,
    displayName:
      sbUser.user_metadata?.full_name ||
      sbUser.user_metadata?.name ||
      sbUser.user_metadata?.user_name ||
      (sbUser.email ? sbUser.email.split("@")[0] : null),
    supabaseUser: sbUser,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRecoveryMode, setIsRecoveryMode] = useState<boolean>(false);

  // Sync profile from backend database via access token
  const syncProfile = async (accessToken: string) => {
    try {
      const p = await getProfile(accessToken);
      setProfile(p);
    } catch (err) {
      console.warn("Backend profile not yet synced or unavailable:", err);
    }
  };

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    // 1. Initial session restoration
    supabase.auth.getSession().then(({ data: { session: initialSession }, error }) => {
      if (error) {
        console.error("Error retrieving Supabase session:", error);
      }
      if (initialSession) {
        setSession(initialSession);
        setUser(mapSupabaseUser(initialSession.user));
        setToken(initialSession.access_token);
        syncProfile(initialSession.access_token);
      }
      setLoading(false);
    });

    // 2. Auth State Change Listener
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, currentSession) => {
      if (event === "PASSWORD_RECOVERY") {
        setIsRecoveryMode(true);
      }

      if (currentSession) {
        setSession(currentSession);
        setUser(mapSupabaseUser(currentSession.user));
        setToken(currentSession.access_token);
        await syncProfile(currentSession.access_token);
      } else {
        setSession(null);
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
      throw new Error("Supabase is not configured. Please verify your environment variables.");
    }
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (error) throw error;
    if (data.session) {
      setSession(data.session);
      setUser(mapSupabaseUser(data.session.user));
      setToken(data.session.access_token);
      await syncProfile(data.session.access_token);
    }
  };

  const signUpWithEmail = async (
    email: string,
    password: string,
    displayName?: string
  ): Promise<{ needsConfirmation: boolean }> => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase is not configured. Please verify your environment variables.");
    }
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: {
          full_name: displayName?.trim() || "",
        },
        emailRedirectTo: getAuthRedirectUrl("/dashboard"),
      },
    });
    if (error) throw error;

    // In Supabase, if email confirmation is enabled, session is null upon signup.
    const needsConfirmation = !data.session;
    if (data.session) {
      setSession(data.session);
      setUser(mapSupabaseUser(data.session.user));
      setToken(data.session.access_token);
      await syncProfile(data.session.access_token);
    }
    return { needsConfirmation };
  };

  const signInWithOAuth = async (provider: "google" | "github") => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase OAuth is not configured. Please verify your environment variables.");
    }
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: getAuthRedirectUrl("/dashboard"),
      },
    });
    if (error) throw error;
    if (data?.url) {
      window.location.href = data.url;
    }
  };

  const resetPasswordForEmail = async (email: string) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase is not configured. Please verify your environment variables.");
    }
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: getAuthRedirectUrl("/reset-password"),
    });
    if (error) throw error;
  };

  const updatePassword = async (newPassword: string) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase is not configured. Please verify your environment variables.");
    }
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    });
    if (error) throw error;
    setIsRecoveryMode(false);
  };

  const signOut = async () => {
    if (isSupabaseConfigured) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setUser(null);
    setProfile(null);
    setToken(null);
    setIsRecoveryMode(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        token,
        loading,
        isConfigured: isSupabaseConfigured,
        isRecoveryMode,
        signInWithEmail,
        signUpWithEmail,
        signInWithOAuth,
        resetPasswordForEmail,
        updatePassword,
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
