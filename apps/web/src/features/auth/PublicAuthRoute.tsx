import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

/**
 * Route wrapper for public authentication pages (Login, SignUp, ForgotPassword).
 * If the user is already authenticated with an active session, redirects them to /dashboard.
 */
export function PublicAuthRoute() {
  const { user, token, loading, isRecoveryMode } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Verifying session...</p>
        </div>
      </div>
    );
  }

  // If already authenticated and not actively recovering a password, redirect to dashboard
  if (user && token && !isRecoveryMode) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
