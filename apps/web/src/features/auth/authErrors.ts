/**
 * Maps Supabase authentication error strings and error objects
 * to friendly, actionable, user-facing error messages.
 */
export function formatAuthError(error: unknown): string {
  if (!error) return "An unexpected error occurred. Please try again.";

  const rawMessage =
    typeof error === "string"
      ? error
      : (error as { message?: string })?.message || String(error);

  const lower = rawMessage.toLowerCase();

  if (
    lower.includes("invalid login credentials") ||
    lower.includes("invalid_credentials")
  ) {
    return "Incorrect email or password. Please verify your credentials and try again.";
  }

  if (
    lower.includes("user already registered") ||
    lower.includes("already registered") ||
    lower.includes("user_already_exists")
  ) {
    return "An account with this email address already exists. Please sign in instead.";
  }

  if (
    lower.includes("email not confirmed") ||
    lower.includes("email_not_confirmed")
  ) {
    return "Please verify your email address before signing in. Check your inbox for the confirmation link.";
  }

  if (
    lower.includes("password should be at least") ||
    lower.includes("weak_password")
  ) {
    return "Password must be at least 8 characters long and contain a mix of letters and numbers.";
  }

  if (
    lower.includes("rate limit") ||
    lower.includes("over_email_send_rate_limit") ||
    lower.includes("once every 60 seconds") ||
    lower.includes("too many requests")
  ) {
    return "Too many requests. For security reasons, please wait a minute before trying again.";
  }

  if (
    lower.includes("auth session missing") ||
    lower.includes("token has expired") ||
    lower.includes("recovery link has expired") ||
    lower.includes("link is invalid") ||
    lower.includes("invalid recovery token")
  ) {
    return "Your password reset session is invalid or has expired. Please request a new reset link.";
  }

  if (
    lower.includes("invalid format") ||
    lower.includes("invalid email") ||
    lower.includes("valid email")
  ) {
    return "Please enter a valid email address (e.g., student@university.edu).";
  }

  if (
    lower.includes("failed to fetch") ||
    lower.includes("network error") ||
    lower.includes("networkrequestfailed")
  ) {
    return "Unable to connect to the authentication service. Please check your network connection.";
  }

  return rawMessage;
}
