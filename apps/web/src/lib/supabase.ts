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

// Fallback to placeholder client if unconfigured to prevent import/runtime crash
export const supabase: SupabaseClient = createClient(
  isSupabaseConfigured ? supabaseUrl : "https://placeholder-project.supabase.co",
  isSupabaseConfigured ? supabaseAnonKey : "placeholder-anon-key"
);
