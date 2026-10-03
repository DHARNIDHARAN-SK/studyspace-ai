import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, CheckCircle, KeyRound, Lock, ShieldAlert } from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { formatAuthError } from "../features/auth/authErrors";
import { Button } from "../components/ui/Button";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const { session, updatePassword, isRecoveryMode } = useAuth();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Check if URL hash or search params contains recovery tokens/code or active session
  const hasRecoveryHash =
    window.location.hash.includes("type=recovery") ||
    window.location.hash.includes("access_token=") ||
    window.location.search.includes("code=");

  const canReset = Boolean(session || isRecoveryMode || hasRecoveryHash);

  // Clear URL hash after processing for security
  useEffect(() => {
    if (window.location.hash.includes("access_token=")) {
      // Allow supabase auth listener a moment to parse the hash
      const timer = setTimeout(() => {
        window.history.replaceState(null, "", window.location.pathname);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    setLoading(true);
    try {
      await updatePassword(password);
      setSuccess(true);
      setTimeout(() => {
        navigate("/dashboard");
      }, 2500);
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center space-x-2.5 mb-3">
          <div className="bg-indigo-600 text-white p-2.5 rounded-xl shadow-xs">
            <BookOpen className="w-6 h-6" />
          </div>
          <span className="text-xl font-bold text-slate-900 tracking-tight">StudySpace AI</span>
        </Link>
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          Create new password
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Choose a secure password for your academic workspace
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white py-8 px-6 shadow-xs border border-slate-200 rounded-xl sm:px-10">
          {error && (
            <div
              role="alert"
              className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-start space-x-2"
            >
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success ? (
            <div className="space-y-4">
              <div
                role="status"
                className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-start space-x-3"
              >
                <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-emerald-900">Password updated successfully!</p>
                  <p className="mt-1 text-emerald-700 leading-relaxed">
                    Your password has been changed. Redirecting to your workspace dashboard...
                  </p>
                </div>
              </div>

              <Button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="w-full"
                size="md"
              >
                Go to Dashboard
              </Button>
            </div>
          ) : !canReset ? (
            <div className="space-y-4 text-center">
              <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg text-left">
                <p className="font-semibold text-amber-900">Reset Session Invalid or Expired</p>
                <p className="mt-1 text-amber-700 leading-relaxed">
                  No active password recovery session was detected. Password recovery links are time-limited for your security.
                </p>
              </div>

              <Link
                to="/forgot-password"
                className="inline-flex items-center justify-center w-full py-2 px-4 border border-transparent rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs"
              >
                Request New Reset Link
              </Link>

              <div className="pt-2">
                <Link
                  to="/login"
                  className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900"
                >
                  <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                  Return to sign in
                </Link>
              </div>
            </div>
          ) : (
            <form className="space-y-4 text-xs" onSubmit={handleSubmit}>
              <div>
                <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  New Password *
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Confirm New Password *
                </label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
              </div>

              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600 space-y-1">
                <p className="font-semibold text-slate-700">Password requirements:</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  <li className={password.length >= 8 ? "text-emerald-600 font-medium" : ""}>
                    At least 8 characters
                  </li>
                  <li
                    className={
                      confirmPassword && password === confirmPassword
                        ? "text-emerald-600 font-medium"
                        : ""
                    }
                  >
                    Passwords match
                  </li>
                </ul>
              </div>

              <Button type="submit" isLoading={loading} className="w-full" size="md">
                Update Password
              </Button>

              <div className="pt-2 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900"
                >
                  <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                  Cancel and sign in
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
