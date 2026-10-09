import { createClient, SupabaseClient } from "@supabase/supabase-js";

function cleanEnvValue(value: unknown): string {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (
    !trimmed ||
    trimmed.includes("your-project-ref") ||
    trimmed.includes("your-anon-key") ||
    trimmed.includes("PASTE_YOUR_") ||
    trimmed.includes("placeholder")
  ) {
    return "";
  }
  return trimmed;
}

const supabaseUrl =
  cleanEnvValue(import.meta.env.VITE_SUPABASE_URL) ||
  cleanEnvValue((import.meta.env as Record<string, string>).SUPABASE_URL) ||
  "";

const supabaseAnonKey =
  cleanEnvValue(import.meta.env.VITE_SUPABASE_ANON_KEY) ||
  cleanEnvValue((import.meta.env as Record<string, string>).SUPABASE_ANON_KEY) ||
  "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

/**
 * Returns the validated base origin/site URL for authentication redirects.
 * In production builds (or when VITE_SITE_URL / window.location is a non-localhost domain),
 * returns the production origin. In local development, returns the local origin.
 */
export function getAuthRedirectUrl(path: string = "/dashboard"): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Priority 1: Explicit site URL configured via environment
  const explicitSiteUrl = cleanEnvValue(import.meta.env.VITE_SITE_URL);
  if (explicitSiteUrl) {
    return `${explicitSiteUrl.replace(/\/+$/, "")}${normalizedPath}`;
  }

  // Priority 2: In browser context, use current origin
  if (typeof window !== "undefined" && window.location?.origin) {
    const origin = window.location.origin.replace(/\/+$/, "");
    return `${origin}${normalizedPath}`;
  }

  // Priority 3: Fallback default
  return `https://studyspace-ai.vercel.app${normalizedPath}`;
}

// Fallback to placeholder client if unconfigured to prevent import/runtime crash
export const supabase: SupabaseClient = createClient(
  isSupabaseConfigured ? supabaseUrl : "https://placeholder-project.supabase.co",
  isSupabaseConfigured ? supabaseAnonKey : "placeholder-anon-key"
);
