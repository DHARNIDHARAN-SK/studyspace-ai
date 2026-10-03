import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookOpen, CheckCircle, Lock, Mail, ShieldAlert, User } from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { Button } from "../components/ui/Button";

export function SignUpPage() {
  const navigate = useNavigate();
  const { user, token, signUpWithEmail } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // If already authenticated, redirect to /dashboard
  useEffect(() => {
    if (user && token) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, token, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      await signUpWithEmail(email, password, displayName);
      setMessage("Account created! Check your email to confirm registration or sign in.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create account");
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
          Create your student account
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Start studying with source-grounded academic intelligence
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

          {message && (
            <div
              role="status"
              className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-lg flex items-start space-x-2"
            >
              <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{message}</span>
            </div>
          )}

          <form className="space-y-4 text-xs" onSubmit={handleSubmit}>
            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Full Name *
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Prof. Evelyn or Student Name"
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                University Email Address *
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@university.edu"
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Password *
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>
            </div>

            <Button type="submit" isLoading={loading} className="w-full" size="md">
              Create Student Account
            </Button>
          </form>

          <div className="mt-5 text-center">
            <span className="text-xs text-slate-500">Already have an account? </span>
            <Link to="/login" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
